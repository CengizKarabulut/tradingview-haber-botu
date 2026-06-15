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

## Tekrar mesaj atma mantigi

Bot haber linklerini `tv_news_cache.json` icinde saklar. Bu yuzden ayni haber normalde tekrar gonderilmez.

Ilk calistirmada eski haber seli olmasin diye en fazla son 10 haber gonderilir. O anda gorunen diger haberler cache'e yazilir ve sonraki turda tekrar gonderilmez.

Sonraki calismalarda yeni ne haber geldiyse Telegram'a gonderilir.

Bildirimlerdeki link haber detay sayfasina degil, dogrudan TradingView haber akisina gider:

```text
https://tr.tradingview.com/news-flow/
```
