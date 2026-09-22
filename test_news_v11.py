import unittest

from bs4 import BeautifulSoup

import news_bot_v11 as v11
from investor_takeaway import summarize_report_text


class InvestorTakeawayTests(unittest.TestCase):
    def test_company_report_turns_fields_into_grounded_takeaway(self):
        text = """
        Şirket Raporu
        Öneri: AL
        Hedef Fiyat: 185,50 TL
        Getiri Potansiyeli: %27,4
        Güçlü ciro büyümesi ve FAVÖK marjındaki iyileşme ana katalizör olarak öne çıkıyor.
        """
        result = summarize_report_text(text, "sirket_raporu")
        joined = " | ".join(result["takeaways"])
        self.assertIn("olumlu", joined)
        self.assertIn("185,50", joined)
        self.assertIn("%27,4", joined)

    def test_hold_recommendation_is_described_as_neutral(self):
        text = "Öneri: TUT\nHedef Fiyat: 92,00 TL\nGetiri Potansiyeli: %5,0"
        result = summarize_report_text(text, "sirket_raporu")
        self.assertIn("nötr", " | ".join(result["takeaways"]))

    def test_technical_report_explains_band_and_breakout_without_new_levels(self):
        text = """
        ASELS için 214,00 destek, 221,50 direnç; 225,00 üzeri kırılımda momentum güçlenebilir.
        BIMAS 705,00 destek seviyesi altında stop-loss, 728,00 ilk direnç olarak izleniyor.
        """
        result = summarize_report_text(text, "teknik_bulten")
        joined = " | ".join(result["takeaways"])
        self.assertIn("214,00", joined)
        self.assertIn("221,50", joined)
        self.assertIn("225,00", joined)
        self.assertNotIn("230", joined)

    def test_model_portfolio_change_becomes_plain_language_takeaway(self):
        text = """
        MODEL PORTFÖY
        ASELS Hedef Fiyat 245,00 TL Getiri Potansiyeli %18
        BIMAS Hedef Fiyat 760,00 TL Getiri Potansiyeli %14
        """
        result = summarize_report_text(
            text,
            "model_portfoy",
            previous_tickers=["ASELS", "THYAO"],
        )
        joined = " | ".join(result["takeaways"])
        self.assertIn("BIMAS", joined)
        self.assertIn("THYAO", joined)
        self.assertIn("değişim", joined.lower())

    def test_daily_report_lists_only_topics_present_in_text(self):
        text = """
        BIST 100 endeksi 10.850 destek ve 11.050 direnç bandında izleniyor.
        TCMB faiz kararı ve enflasyon görünümü günün ana gündeminde.
        """
        result = summarize_report_text(text, "gunluk_bulten")
        joined = " | ".join(result["takeaways"])
        self.assertIn("BIST 100", joined)
        self.assertIn("faiz", joined)
        self.assertIn("enflasyon", joined)
        self.assertNotIn("petrol", joined.lower())

    def test_empty_text_has_no_takeaway(self):
        result = summarize_report_text("", "teknik_bulten")
        self.assertEqual(result["takeaways"], [])

    def test_caption_separates_takeaway_from_source_facts_and_keeps_pdf_link(self):
        item = {
            "source": "akyatirim",
            "report_type": "sirket_raporu",
            "title": "ASELS Şirket Raporu",
            "date_text": "05.09.2026",
            "published_date": "2026-09-05",
            "page_url": "https://www.akyatirim.com.tr/arastirma/rapor",
            "document_url": "https://www.akyatirim.com.tr/arastirma/rapor.pdf",
        }
        summary = {
            "takeaways": ["Kurumun rapordaki görüşü olumlu (AL); hedef fiyat 245,00 TL; getiri potansiyeli %18."],
            "bullets": ["Öneri: AL", "Hedef fiyat: 245,00", "Getiri potansiyeli: %18"],
            "meta": {},
        }
        caption = v11._summary_caption(item, summary)
        self.assertIn("Yatırımcı için anlamı", caption)
        self.assertIn("Rapordan öne çıkanlar", caption)
        self.assertIn("Resmî araştırma kaynağını aç", caption)
        self.assertLessEqual(len(caption), v11.SUMMARY_CAPTION_LIMIT)


class KapFormattingTests(unittest.TestCase):
    def _kap_soup(self):
        return BeautifulSoup(
            """
            <div class="disclosureScrollableArea">
              <span>[CONSOLIDATION METHOD TITLE]</span>
              <span>oda_DefaultTransactionTransactionType1</span>
              <span>Temerrüt İşleminin Tamamlanması (Completion of Default Transaction)</span>
              <span>oda_RelatedMarket1</span>
              <span>PAY PİYASASI</span>
              <span>oda_SettlementDate1</span>
              <span>2026-09-22</span>
              <span>oda_DateOfThePreviousNotificationAboutTheSameSubject1</span>
              <span>22/09/2026</span>
              <span>oda_ExplanationTextBlock1</span>
              <span>ASELS.TE sırasındaki temerrüt işlemi 22/09/2026 tarihinde tamamlanmıştır.</span>
            </div>
            """,
            "html.parser",
        )

    def test_kap_detail_keeps_only_readable_fields(self):
        detail = v11.compact_kap_detail(self._kap_soup())
        self.assertIn("İşlem Türü: Temerrüt İşleminin Tamamlanması", detail)
        self.assertIn("İlgili Pazar: PAY PİYASASI", detail)
        self.assertIn("Takas Tarihi: 22.09.2026", detail)
        self.assertIn("Önceki Açıklama: 22.09.2026", detail)
        self.assertIn("Açıklama: ASELS.TE", detail)
        self.assertNotIn("oda_", detail)
        self.assertNotIn("Completion of Default Transaction", detail)
        self.assertNotIn("CONSOLIDATION", detail)

    def test_kap_message_is_grouped_and_does_not_leak_form_tokens(self):
        v11.install_message_formatting()
        detail = v11.compact_kap_detail(self._kap_soup())
        item = {
            "source": "kap",
            "title": "ASELS — Temerrüt İşlemi",
            "provider": "İSTANBUL TAKAS VE SAKLAMA BANKASI A.Ş.",
            "published": "2026-09-22T15:50:57+03:00",
            "summary": "İşleme Açılan Temerrüt Sırası · Şirket: İSTANBUL TAKAS VE SAKLAMA BANKASI A.Ş.",
            "detail": detail,
            "link": "https://www.kap.org.tr/tr/Bildirim/1666607",
            "attachment_count": 0,
        }
        message = v11.layered_build_message(item)
        self.assertIn("TEMERRÜT İŞLEMİ", message)
        self.assertIn("📌 <b>İşlem bilgileri</b>", message)
        self.assertIn("ℹ️ <b>Açıklama</b>", message)
        self.assertIn("KAP bildiriminin tamamını aç", message)
        self.assertNotIn("oda_", message)
        self.assertNotIn("CONSOLIDATION", message)
        self.assertNotIn("Completion of Default Transaction", message)


class UnifiedNewsFormattingTests(unittest.TestCase):
    def setUp(self):
        v11.install_message_formatting()

    def test_market_news_uses_one_clean_card_without_source_repetition(self):
        item = {
            "source": "bloomberght",
            "title": "BIST 100 güne yükselişle başladı",
            "provider": "Bloomberg HT",
            "published": "2026-09-22T10:05:00+03:00",
            "category": "",
            "summary": "BIST 100 güne yükselişle başladı. Bankacılık ve sanayi hisselerinde alımlar öne çıktı.",
            "detail": "BIST 100 güne yükselişle başladı. Bankacılık ve sanayi hisselerinde alımlar öne çıktı. Endeks günün ilk bölümünde pozitif seyretti.",
            "link": "https://www.bloomberght.com/ornek",
        }
        message = v11.layered_build_message(item)
        self.assertIn("📰 <b>PİYASA HABERİ | Bloomberg HT</b>", message)
        self.assertIn("📝 <b>Özet</b>", message)
        self.assertIn("ℹ️ <b>Detay</b>", message)
        self.assertIn("Haberi kaynağında aç", message)
        self.assertNotIn("🏢 Bloomberg HT", message)
        self.assertEqual(message.count("PİYASA HABERİ | Bloomberg HT"), 1)

    def test_official_notice_avoids_generic_summary_noise(self):
        item = {
            "source": "tcmb",
            "title": "Para Politikası Kurulu Kararı",
            "provider": "TCMB",
            "published": "2026-09-22T14:00:00+03:00",
            "category": "Basın Duyurusu",
            "summary": "Türkiye Cumhuriyet Merkez Bankası resmî duyurusu",
            "detail": "",
            "link": "https://www.tcmb.gov.tr/ornek",
        }
        message = v11.layered_build_message(item)
        self.assertIn("🏛 <b>RESMÎ | TCMB</b>", message)
        self.assertIn("Resmî duyuruyu aç", message)
        self.assertNotIn("Türkiye Cumhuriyet Merkez Bankası resmî duyurusu", message)

    def test_economic_calendar_turns_dot_separated_values_into_bullets(self):
        item = {
            "source": "forexfactory",
            "title": "USD — Fed Faiz Kararı",
            "provider": "Yaklaşan yüksek etkili olay",
            "published": "2026-09-22T21:00:00+03:00",
            "summary": "Yaklaşık 45 dakika sonra · Etki: Yüksek · Beklenti: %4,75 · Önceki: %5,00",
            "detail": "",
            "link": "https://www.forexfactory.com/calendar",
        }
        message = v11.layered_build_message(item)
        self.assertIn("🗓 <b>EKONOMİK TAKVİM | Forex Factory</b>", message)
        self.assertIn("📌 <b>Takvim bilgileri</b>", message)
        self.assertIn("• Etki: Yüksek", message)
        self.assertIn("• Beklenti: %4,75", message)
        self.assertIn("Ekonomik takvim kaynağını aç", message)

    def test_long_news_text_stays_within_telegram_limit(self):
        item = {
            "source": "tradingview",
            "title": "Uzun haber",
            "provider": "TradingView",
            "published": "2026-09-22T12:00:00+03:00",
            "summary": "Özet " + ("x" * 3000),
            "detail": "Detay " + ("y" * 6000),
            "link": "https://tr.tradingview.com/news/ornek/",
        }
        message = v11.layered_build_message(item)
        self.assertLessEqual(len(message), 3900)
        self.assertTrue(message.endswith("</a>"))


if __name__ == "__main__":
    unittest.main()
