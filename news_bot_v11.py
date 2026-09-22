"""v11: PDF + kısa özet akışına kontrollü 'yatırımcı için anlamı' katmanı ekler.

v10'un PDF gönderimini, tarih/tekrar filtrelerini ve extractive özetini korur.
Yeni katman yalnız PDF içinde bulunan somut öneri, hedef, destek/direnç, kırılım/stop
ve model-portföy değişimlerinden kısa bir anlam çıkarır; serbest yatırım tavsiyesi üretmez.

Telegram haber akışı da tek bir okunabilir kart düzenine getirilir:
- KAP'ın teknik oda_ alanları, İngilizce tekrarları ve form metadatası temizlenir.
- Resmî duyuru, hızlı piyasa, ekonomi, global haber ve ekonomik takvim kaynakları
  aynı görsel hiyerarşiyi kullanır.
- Başlık/kaynak tekrarları bastırılır; uzun ham metin yerine kısa ve okunabilir özet verilir.
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

KAP_ODA_FIELDS = (
    ("oda_DefaultTransactionTransactionType", "İşlem Türü"),
    ("oda_RelatedMarket", "İlgili Pazar"),
    ("oda_SettlementDate", "Takas Tarihi"),
    ("oda_DateOfThePreviousNotificationAboutTheSameSubject", "Önceki Açıklama"),
)

GENERIC_SUMMARIES = {
    "borsa istanbul resmî duyurusu",
    "borsa istanbul resmi duyurusu",
    "türkiye cumhuriyet merkez bankası resmî duyurusu",
    "türkiye cumhuriyet merkez bankası resmi duyurusu",
    "sermaye piyasası kurulu resmî bülteni",
    "sermaye piyasası kurulu resmi bülteni",
}

SOURCE_HEADER_OVERRIDES = {
    "bloomberght": ("📰", "PİYASA HABERİ", "Bloomberg HT"),
    "cnbce": ("📰", "PİYASA HABERİ", "CNBC-e"),
    "aaekonomi": ("📰", "EKONOMİ", "Anadolu Ajansı"),
    "investing": ("📰", "PİYASA HABERİ", "Investing.com Türkiye"),
    "ntvpara": ("📰", "PİYASA HABERİ", "NTV Para"),
    "trthaber": ("📰", "EKONOMİ", "TRT Haber Ekonomi"),
    "tradingview": ("⚡", "PİYASA AKIŞI", "TradingView"),
}

OFFICIAL_SOURCES = {"bist", "tcmb", "tuik", "spk"}


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


def _excerpt(value, max_chars):
    """Metni kelime/cümle ortasında sert kesmeden Telegram için kısalt."""
    value = clean(value)
    if len(value) <= max_chars:
        return value

    window = value[: max_chars + 1]
    sentence_cut = max(window.rfind(". "), window.rfind("! "), window.rfind("? "))
    if sentence_cut >= int(max_chars * 0.55):
        return window[: sentence_cut + 1].rstrip()

    word_cut = window.rfind(" ")
    if word_cut < int(max_chars * 0.55):
        word_cut = max_chars
    return window[:word_cut].rstrip(" ,;:-") + "…"


def _plain_compare(value):
    return re.sub(r"\s+", " ", clean(value)).strip().casefold().replace("i̇", "i")


def _strip_title_prefix(value, title):
    value = clean(value)
    title = clean(title)
    if not value or not title:
        return value
    lower_value, lower_title = value.casefold(), title.casefold()
    if lower_value == lower_title:
        return ""
    if lower_value.startswith(lower_title):
        remainder = value[len(title):].lstrip(" \t\r\n-—:|·")
        if len(remainder) >= 20:
            return remainder
    return value


def _prepare_news_texts(item):
    title = clean(item.get("title"))
    summary = _strip_title_prefix(item.get("summary"), title)
    detail = _strip_title_prefix(item.get("detail"), title)

    if _plain_compare(summary) in GENERIC_SUMMARIES:
        summary = ""

    if summary and detail:
        summary_cmp = _plain_compare(summary)
        detail_cmp = _plain_compare(detail)
        if summary_cmp == detail_cmp:
            detail = ""
        elif detail_cmp.startswith(summary_cmp):
            detail = clean(detail[len(summary):]).lstrip(" .·-—:|")
        elif summary_cmp.startswith(detail_cmp):
            detail = ""

    return _excerpt(summary, 520), _excerpt(detail, 760)


def _source_header(item):
    source = item.get("source", "")
    if source in SOURCE_HEADER_OVERRIDES:
        return SOURCE_HEADER_OVERRIDES[source]

    layer = v6.LAYER_INFO.get(source)
    if layer:
        return layer

    label = base.SOURCE_LABELS.get(source) or clean(item.get("provider")) or source or "Haber"
    return "📰", "HABER", label


def _provider_is_redundant(provider, label):
    provider_cmp = _plain_compare(provider)
    label_cmp = _plain_compare(label)
    if not provider_cmp or not label_cmp:
        return True
    return provider_cmp == label_cmp or label_cmp in provider_cmp or provider_cmp in label_cmp


def _news_link_label(source):
    if source in OFFICIAL_SOURCES:
        return "Resmî duyuruyu aç"
    if source == "forexfactory":
        return "Ekonomik takvim kaynağını aç"
    return "Haberi kaynağında aç"


def _build_kap_message(item):
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
        parts.extend(["", f"📝 <b>Özet:</b> {html.escape(_excerpt(summary, 520))}"])

    if fields:
        parts.extend(["", "📌 <b>İşlem bilgileri</b>"])
        for label, value in fields[:6]:
            parts.append(f"• <b>{html.escape(label)}:</b> {html.escape(_excerpt(value, 260))}")
    elif facts:
        parts.extend(["", "🔎 <b>Öne çıkan:</b> " + " · ".join(html.escape(value) for value in facts)])

    if explanation:
        parts.extend(["", "ℹ️ <b>Açıklama</b>", html.escape(_excerpt(explanation, 900))])
    elif item.get("detail"):
        compact = clean(item.get("detail"))
        if compact and compact.lower() != summary.lower():
            parts.extend(["", "ℹ️ <b>Detay</b>", html.escape(_excerpt(compact, 700))])

    if item.get("attachment_count"):
        parts.extend(["", f"📎 {int(item['attachment_count'])} ek"])

    parts.extend([
        "",
        f'<a href="{html.escape(item["link"], quote=True)}">KAP bildiriminin tamamını aç</a>',
    ])
    return _fit_message(parts)


def _build_calendar_message(item, icon, layer_name, label):
    title = clean(item.get("title")) or "Ekonomik Takvim"
    published = base.format_date(item.get("published"))
    provider = clean(item.get("provider"))
    summary = clean(item.get("summary"))
    values = [clean(value) for value in re.split(r"\s*·\s*", summary) if clean(value)]

    parts = [
        f"{icon} <b>{html.escape(layer_name)} | {html.escape(label)}</b>",
        f"<b>{html.escape(title)}</b>",
    ]
    if published:
        parts.append(f"🕒 {html.escape(published)}")
    if provider and not _provider_is_redundant(provider, label):
        parts.append(f"🔔 {html.escape(provider)}")

    if values:
        parts.extend(["", "📌 <b>Takvim bilgileri</b>"])
        for value in values[:6]:
            parts.append(f"• {html.escape(_excerpt(value, 220))}")

    parts.extend([
        "",
        f'<a href="{html.escape(item["link"], quote=True)}">{_news_link_label(item.get("source"))}</a>',
    ])
    return _fit_message(parts)


def _build_news_message(item):
    source = item.get("source", "")
    icon, layer_name, label = _source_header(item)

    if source == "forexfactory":
        return _build_calendar_message(item, icon, layer_name, label)

    title = clean(item.get("title")) or "Haber"
    published = base.format_date(item.get("published"))
    provider = clean(item.get("provider"))
    category = clean(item.get("category"))
    summary, detail = _prepare_news_texts(item)

    parts = [
        f"{icon} <b>{html.escape(layer_name)} | {html.escape(label)}</b>",
        f"<b>{html.escape(title)}</b>",
    ]

    meta = []
    if published:
        meta.append(f"🕒 {html.escape(published)}")
    if category and _plain_compare(category) not in {
        _plain_compare(layer_name),
        _plain_compare(label),
        "resmî duyuru",
        "resmi duyuru",
    }:
        meta.append(f"🏷 {html.escape(category)}")
    if provider and not _provider_is_redundant(provider, label):
        meta.append(f"🏢 {html.escape(provider)}")
    parts.extend(meta)

    if summary:
        parts.extend(["", "📝 <b>Özet</b>", html.escape(summary)])
    if detail:
        parts.extend(["", "ℹ️ <b>Detay</b>", html.escape(detail)])

    if item.get("attachment_count"):
        parts.extend(["", f"📎 {int(item['attachment_count'])} ek"])

    parts.extend([
        "",
        f'<a href="{html.escape(item["link"], quote=True)}">{_news_link_label(source)}</a>',
    ])
    return _fit_message(parts)


def _fit_message(parts, limit=3900):
    """HTML etiketlerini bölmeden Telegram sınırına sığdır."""
    message = "\n".join(parts)
    if len(message) <= limit:
        return message

    link = parts[-1] if parts else ""
    kept = []
    reserve = len(link) + 2
    for line in parts[:-1]:
        candidate = "\n".join(kept + [line])
        if len(candidate) + reserve <= limit:
            kept.append(line)
    while kept and not kept[-1]:
        kept.pop()
    return "\n".join(kept + ["", link])


def layered_build_message(item):
    if item.get("source") == "kap":
        return _build_kap_message(item)
    return _build_news_message(item)


def install_message_formatting():
    if not any(rule[0] == "temerrut" for rule in v6.KAP_KIND_RULES):
        v6.KAP_KIND_RULES = (
            (
                "temerrut", "⚠️", "TEMERRÜT İŞLEMİ",
                ("temerrüt", "temerrut", "default transaction"),
            ),
        ) + v6.KAP_KIND_RULES

    v4.compact_kap_detail = compact_kap_detail
    v6.layered_build_message = layered_build_message


def install_kap_formatting():
    """Eski test/çağrılar için geriye dönük uyum."""
    install_message_formatting()


def install_takeaway_layer():
    v10.summarize_report_text = summarize_report_text
    v10._summary_caption = _summary_caption


def main():
    install_message_formatting()
    install_takeaway_layer()
    v10.main()


if __name__ == "__main__":
    main()
