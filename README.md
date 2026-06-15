# TradingView Haber Botu

TradingView genel haber akisindan gelen yeni haberleri Telegram'a gonderen GitHub Actions botu.

Kaynak:

```text
https://tr.tradingview.com/news-flow/
```

## Calisma sikligi

Bot GitHub Actions uzerinde 15 dakikada bir calisir.

```yaml
cron: '*/15 * * * *'
```

Istersen GitHub Actions ekranindan elle de calistirabilirsin.

## Gerekli GitHub Secrets

Repo ayarlarinda `Settings > Secrets and variables > Actions > New repository secret` bolumune su secret'lar eklenmeli:

```text
TELEGRAM_TOKEN
TELEGRAM_CHAT_ID
TELEGRAM_MESSAGE_THREAD_ID
```

`TELEGRAM_TOKEN`, BotFather'dan aldigin bot tokenidir.

`TELEGRAM_CHAT_ID`, mesajlarin gidecegi grup veya kanal ID'sidir. Grup ID'leri genelde `-100...` ile baslar.

`TELEGRAM_MESSAGE_THREAD_ID`, mesajlarin gidecegi Telegram konu ID'sidir. Konu kullanmiyorsan bos birakabilirsin.

Bu bot icin paylasilan konu URL'sinden cikan degerler:

```text
TELEGRAM_CHAT_ID=-1003502567927
TELEGRAM_MESSAGE_THREAD_ID=18410
```

## Haber cekme ve tekrar mesaj atma mantigi

Bot haberleri ana TradingView haber akisindan okur:

```text
https://tr.tradingview.com/news-flow/
```

Telegram bildirimindeki link ise ilgili haberin kendi TradingView detay sayfasina gider.

Bot `tv_news_cache.json` icinde en son gorulen haber linkini `last_seen_key` olarak saklar.

Ilk calistirmada eski haber seli olmasin diye mesaj gondermez; sadece ana akistaki en ust haberi referans alir.

Sonraki calismalarda ana akista bu son gorulen haberin ustune gelen yeni haberleri Telegram'a gonderir.

Cache formati:

```text
{
  "last_seen_key": "...",
  "seen_keys": []
}
```
