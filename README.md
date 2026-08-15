# KAP, Bloomberg HT ve TradingView Haber Botu

Resmî KAP bildirimlerini, Bloomberg HT ekonomi haberlerini ve TradingView Türkçe haber akışını Telegram'a gönderir.

## Kaynaklar

- KAP: `https://www.kap.org.tr/tr/api/disclosure/members/byCriteria`
- Bloomberg HT: `https://www.bloomberght.com/tumhaberler`
- TradingView: `https://tr.tradingview.com/news-flow/`

KAP ana ve resmî şirket bildirimi kaynağıdır. KAP sorgu yapısı için MIT lisanslı
[`pykap`](https://github.com/cemsinano/pykap) ve
[`borsajs`](https://github.com/mesutpiskin/borsajs) projelerindeki güncel entegrasyon
yaklaşımları referans alınmıştır. Bot bu paketleri bağımlılık olarak kurmaz.

## Telegram mesajları

Mesajlarda mümkün olduğunda kaynak, yayın zamanı, şirket, başlık, kısa özet,
sınırlı haber ayrıntısı, KAP ek sayısı ve kaynak bağlantısı bulunur. Tam makaleler
yeniden yayımlanmaz. Telegram bağlantı ve büyük görsel önizlemesi açıktır.

## GitHub Secrets

`Settings > Secrets and variables > Actions` altında:

```text
TELEGRAM_TOKEN
TELEGRAM_CHAT_ID
TELEGRAM_MESSAGE_THREAD_ID
```

`TELEGRAM_MESSAGE_THREAD_ID` yalnızca Telegram forum konusu kullanılıyorsa gereklidir.

## İsteğe bağlı ortam değişkenleri

```text
NEWS_SOURCES=kap,bloomberght,tradingview
NEWS_LIMIT=100
PER_RUN_SEND_LIMIT=30
DETAIL_MAX_CHARS=1800
TELEGRAM_SEND_DELAY=4
```

## Cache ve ilk çalışma

Her kaynak `news_cache.json` içinde ayrı takip edilir. Yeni kaynak ilk çalışmada eski
haberleri göndermez. Bir kaynak hata verirse diğerleri çalışmaya devam eder ve
başarısız kaynağın cache'i ilerletilmez.

## Yerel test

```bash
pip install -r requirements.txt
DRY_RUN=1 python news_bot.py
```

PowerShell:

```powershell
$env:DRY_RUN='1'
python news_bot.py
```
