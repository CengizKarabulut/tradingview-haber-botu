"""v11: PDF + kısa özet akışına kontrollü 'yatırımcı için anlamı' katmanı ekler.

v10'un PDF gönderimini, tarih/tekrar filtrelerini ve extractive özetini korur.
Yeni katman yalnız PDF içinde bulunan somut öneri, hedef, destek/direnç, kırılım/stop
ve model-portföy değişimlerinden kısa bir anlam çıkarır; serbest yatırım tavsiyesi üretmez.

Ayrıca KAP bildirimlerini Telegram'da okunabilir hale getirir: KAP'ın teknik oda_ alanları,
İngilizce tekrarları ve form metadatası gösterilmez; önemli alanlar ve açıklama ayrı satırlarda sunulur.
"""

import html
import re

import news_bot as base
import news_bot_v4 as v4
import news_bot_v6 as v6
import news_bot_v10 as v10
from investor_takeaway import summarize_report_text


SUMMARY_CAPTION_LIMIT = v10.SUMMARY_CAPTION_LIMIT
ORIGINAL_KAP_COMPACT = v4.compact_kap_detail
ORIGINAL_LAYERED_BUILD_MESSAGE = v6.layered_build_message

KAP_ODA_FIELDS = (
    ("oda_DefaultTransactionTransactionType", "İşlem Türü"),
    ("oda_RelatedMarket", "İlgili Pazar"),
    ("oda_SettlementDate", "Takas Tarihi"),
    ("oda_DateOfThePreviousNotificationAboutTheSameSubject", "Önceki Açıklama"),
)


def clean(value):
    return base.clean(value)


def _summary_caption(item, summary, extraction_error=""):
    source = item.get("source", "")
    label = (
        v6.RESEARCH_PAGE_CONFIGS.get(source, {}).get("label")
        or v4.BULLETIN_LABELS.get(source, source)
    )
    icon, report_label = v6.report_type_meta(item)
    date_text = item.get("date_text") or item.get("published_date") or ""
    title = clean(item.get("title"))
    page_url = item.get("page_url") or item.get("document_url")

    lines = [
        f"📚 <b>ARAŞTIRMA | {html.escape(label)}</b>",
        f"{icon} <b>{html.escape(report_label)}</b>",
    ]
    if date_text:
        lines.append(f"🗓 {html.escape(date_text)}")
    if title and report_label.lower() not in title.lower():
        lines.append(f"📝 {html.escape(title[:150])}")

    takeaways = list(summary.get("takeaways") or [])
    if takeaways:
        lines.append("👀 <b>Yatırımcı için anlamı:</b>")
        for takeaway in takeaways[:2]:
            lines.append("• " + html.escape(clean(takeaway)[:240]))

    bullets = list(summary.get("bullets") or [])
    if bullets:
        lines.append("🧾 <b>Rapordan öne çıkanlar:</b>")
        for bullet in bullets[:4]:
            lines.append("• " + html.escape(clean(bullet)[:220]))
    elif extraction_error:
        lines.append("🧾 PDF ektedir; metin katmanı otomatik okunamadığı için içerik özeti üretilmedi.")
    else:
        lines.append("🧾 PDF ektedir; güvenilir bir kısa özet çıkaracak yeterli metin bulunamadı.")

    link_line = f'<a href="{html.escape(page_url, quote=True)}">Resmî araştırma kaynağını aç</a>'
    return v10._fit_caption(lines, link_line, limit=SUMMARY_CAPTION_LIMIT)


def _strip_english_parenthetical(value):
    """KAP'ın Türkçe değerin sonuna eklediği kısa İngilizce karşılığı kaldır."""
    value = clean(value)
    match = re.search(r"\s+\(([^()]*)\)\s*$", value)
    if not match:
        return value
    inner = match.group(1).strip()
    if inner and re.fullmatch(r"[A-Za-z0-9 /&.,'’:+-]+", inner):
        return value[:match.start()].strip()
    return value


def _format_kap_date(value):
    value = clean(value)
    iso = re.fullmatch(r"(20\d{2})-(\d{2})-(\d{2})", value)
    if iso:
        return f"{iso.group(3)}.{iso.group(2)}.{iso.group(1)}"
    slash = re.fullmatch(r"(\d{2})/(\d{2})/(20\d{2})", value)
    if slash:
        return f"{slash.group(1)}.{slash.group(2)}.{slash.group(3)}"
    return value


def _extract_oda_value(flat_text, key):
    pattern = re.compile(
        rf"\b{re.escape(key)}(?:\[\d+\]|\d+)?\s+(.+?)(?=\s+oda_[A-Za-z0-9_().\[\]-]+\b|$)",
        re.IGNORECASE,
    )
    match = pattern.search(flat_text)
    if not match:
        return ""
    return _strip_english_parenthetical(match.group(1))


def _clean_explanation(value):
    value = clean(value)
    if not value:
        return ""
    # KAP'ın standart hukuki kapanış metinleri Telegram özetine taşınmasın.
    lowered = value.lower()
    cut_points = []
    for prefix in v4.KAP_BOILERPLATE_STARTS:
        index = lowered.find(prefix)
        if index >= 0:
            cut_points.append(index)
    if cut_points:
        value = value[:min(cut_points)].strip(" .·")
    return value


def compact_kap_detail(soup):
    """KAP'ın teknik form çıktısını insan okunur kısa alanlara dönüştür."""
    content = soup.select_one(".disclosureScrollableArea")
    if not content:
        return ""

    for node in content.select("script, style, input, button, svg, noscript"):
        node.decompose()

    flat_text = clean(content.get_text(" ", strip=True))
    lines = []

    for key, label in KAP_ODA_FIELDS:
        value = _extract_oda_value(flat_text, key)
        if not value:
            continue
        if label in {"Takas Tarihi", "Önceki Açıklama"}:
            value = _format_kap_date(value)
        lines.append(f"{label}: {value}")

    explanation = _extract_oda_value(flat_text, "oda_ExplanationTextBlock")
    explanation = _clean_explanation(explanation)
    if explanation:
        lines.append(f"Açıklama: {explanation}")

    if lines:
        return "\n".join(lines)[:1600]

    # ODA anahtarları olmayan eski KAP şablonlarında mevcut güvenli yedeği koru.
    fallback = ORIGINAL_KAP_COMPACT(soup)
    fallback = v4.KAP_SYSTEM_TOKEN.sub(" ", fallback)
    return clean(fallback)[:900]


def _split_kap_detail(detail):
    fields = []
    explanation = ""
    for raw in str(detail or "").splitlines():
        line = raw.strip()
        if not line:
            continue
        if ":" not in line:
            if not explanation:
                explanation = clean(line)
            continue
        label, value = line.split(":", 1)
        label, value = clean(label), clean(value)
        if not value:
            continue
        if label.lower() == "açıklama":
            explanation = value
        else:
            fields.append((label, value))
    return fields, explanation


def layered_build_message(item):
    if item.get("source") != "kap":
        return ORIGINAL_LAYERED_BUILD_MESSAGE(item)

    title = clean(item.get("title")) or "KAP Bildirimi"
    ticker, subject = "", title
    if " — " in title:
        ticker, subject = [part.strip() for part in title.split(" — ", 1)]

    company = clean(item.get("provider"))
    published = base.format_date(item.get("published"))
    summary = v4._strip_company_from_summary(item.get("summary"), company)
    fields, explanation = _split_kap_detail(item.get("detail"))

    _, kind_icon, kind_label = v6.classify_kap(item)
    facts = v6.smart_kap_facts(item)

    parts = [
        f"🏛 <b>RESMÎ | KAP{f' | {html.escape(ticker)}' if ticker else ''}</b>",
        f"{kind_icon} <b>{html.escape(kind_label)}</b>",
        f"<b>{html.escape(subject)}</b>",
        "",
    ]

    meta = []
    if company and company.lower() != "kap":
        meta.append(f"🏢 {html.escape(company)}")
    if published:
        meta.append(f"🕒 {html.escape(published)}")
    parts.extend(meta)

    if summary and summary.lower() not in {subject.lower(), title.lower()}:
        parts.extend(["", f"📝 <b>Özet:</b> {html.escape(summary)}"])

    if fields:
        parts.extend(["", "📌 <b>İşlem bilgileri</b>"])
        for label, value in fields[:6]:
            parts.append(f"• <b>{html.escape(label)}:</b> {html.escape(value)}")
    elif facts:
        parts.extend(["", "🔎 <b>Öne çıkan:</b> " + " · ".join(html.escape(value) for value in facts)])

    if explanation:
        parts.extend(["", "ℹ️ <b>Açıklama</b>", html.escape(explanation[:900])])
    elif item.get("detail"):
        compact = clean(item.get("detail"))
        if compact and compact.lower() != summary.lower():
            parts.extend(["", "ℹ️ <b>Detay</b>", html.escape(compact[:700])])

    if item.get("attachment_count"):
        parts.extend(["", f"📎 {int(item['attachment_count'])} ek"])

    parts.extend([
        "",
        f'<a href="{html.escape(item["link"], quote=True)}">KAP bildiriminin tamamını aç</a>',
    ])

    message = "\n".join(parts)
    if len(message) <= 3900:
        return message

    link = parts[-1]
    return message[:3700].rstrip() + "…\n\n" + link


def install_kap_formatting():
    if not any(rule[0] == "temerrut" for rule in v6.KAP_KIND_RULES):
        v6.KAP_KIND_RULES = (
            (
                "temerrut", "⚠️", "TEMERRÜT İŞLEMİ",
                ("temerrüt", "temerrut", "default transaction"),
            ),
        ) + v6.KAP_KIND_RULES

    v4.compact_kap_detail = compact_kap_detail
    v6.layered_build_message = layered_build_message


def install_takeaway_layer():
    # v10.send_research_item bu iki ismi kendi modül globalinden runtime'da okur.
    v10.summarize_report_text = summarize_report_text
    v10._summary_caption = _summary_caption


def main():
    install_kap_formatting()
    install_takeaway_layer()
    v10.main()


if __name__ == "__main__":
    main()
