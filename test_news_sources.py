import os
import unittest

os.environ["DRY_RUN"] = "1"

import news_bot


class SourceAndDuplicateTests(unittest.TestCase):
    def test_source_priority_is_fixed(self):
        self.assertEqual(
            news_bot.ENABLED_SOURCES,
            ["kap", "bloomberght", "investing", "ntvpara", "trthaber", "tradingview"],
        )

    def test_similar_cross_source_story_is_duplicate(self):
        kap = news_bot.blank_item(
            "kap",
            "THYAO — Yeni uçak alımına ilişkin açıklama",
            "https://kap/1",
            summary="Türk Hava Yolları yeni uçak alım kararı aldı.",
        )
        bloomberg = news_bot.blank_item(
            "bloomberght",
            "THYAO yeni uçak alım kararı aldı",
            "https://bloomberg/1",
            summary="Türk Hava Yolları yeni uçak alımına ilişkin açıklama yaptı.",
        )
        history = []
        news_bot.remember_story(kap, history)
        self.assertTrue(news_bot.is_cross_source_duplicate(bloomberg, history))

    def test_unrelated_story_is_not_duplicate(self):
        history = []
        news_bot.remember_story(
            news_bot.blank_item("kap", "ASELS yeni sözleşme imzaladı", "https://kap/1"),
            history,
        )
        unrelated = news_bot.blank_item(
            "investing", "Euro Bölgesi enflasyonu geriledi", "https://investing/1"
        )
        self.assertFalse(news_bot.is_cross_source_duplicate(unrelated, history))

    def test_rss_is_parsed_and_html_summary_is_cleaned(self):
        xml = """<?xml version="1.0" encoding="UTF-8"?>
        <rss><channel><item><title>Dolar/TL hareketlendi</title>
        <link>https://example.com/dolar</link><guid>fx-1</guid>
        <pubDate>Sat, 15 Aug 2026 10:00:00 GMT</pubDate>
        <description><![CDATA[<p>Kurda yeni hareket görüldü.</p>]]></description>
        </item></channel></rss>""".encode("utf-8")
        items = news_bot.fetch_rss_source("ntvpara", _Session(_Response(xml)))
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["summary"], "Kurda yeni hareket görüldü.")

    def test_atom_feed_is_parsed(self):
        xml = """<?xml version="1.0" encoding="UTF-8"?>
        <feed xmlns="http://www.w3.org/2005/Atom"><entry>
        <title>Piyasalarda gün ortası</title>
        <link rel="alternate" href="https://example.com/piyasa" />
        <id>atom-1</id><updated>2026-08-15T11:00:00+03:00</updated>
        <summary>Endeks ve döviz piyasaları izlendi.</summary>
        </entry></feed>""".encode("utf-8")
        items = news_bot.fetch_rss_source("ntvpara", _Session(_Response(xml)))
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["link"], "https://example.com/piyasa")
        self.assertEqual(items[0]["id"], "atom-1")


class _Response:
    def __init__(self, content):
        self.content = content

    def raise_for_status(self):
        return None


class _Session:
    def __init__(self, response):
        self.response = response

    def get(self, *args, **kwargs):
        return self.response


if __name__ == "__main__":
    unittest.main()
