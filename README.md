# Çok Kaynaklı Finans Haber Botu

KAP bildirimlerini ve Türkçe ekonomi/piyasa haberlerini öncelik sırasıyla Telegram'a gönderir.

## Kaynaklar ve öncelik

1. KAP (resmî şirket bildirimleri)
2. Bloomberg HT
3. Investing.com Türkiye (genel, forex ve hisse RSS akışları)
4. NTV Para
5. TRT Haber Ekonomi
6. TradingView

Kaynak sırası sabittir; `NEWS_SOURCES` farklı sırada verilse de bot bu güven sırasını korur.
Foreks'in herkese açık RSS adresi otomatik istemcilere `403` döndürdüğü için kırılgan bir kazıyıcı
eklenmemiştir.

KAP sorgu yapısı için MIT lisanslı
[`pykap`](https://github.com/cemsinano/pykap) ve
[`borsajs`](https://github.com/mesutpiskin/borsajs) projelerindeki güncel entegrasyon
yaklaşımları referans alınmıştır. Bot bu paketleri bağımlılık olarak kurmaz.

## Tekrar haber filtresi

Bot önce aynı kaynaktaki kimlik, bağlantı ve başlık tekrarlarını kaldırır. Sonra başlık ile kısa
özeti normalize ederek kaynaklar arasında benzerlik karşılaştırması yapar. Aynı olay daha düşük
öncelikli bir kaynakta tekrar görülürse Telegram'a yeniden gönderilmez. Son 1.500 haber izi
`news_cache.json` içinde tutulur.

## Telegram mesajları

Mesajlarda mümkün olduğunda kaynak, yayın zamanı, şirket, başlık, kısa özet, sınırlı haber
ayrıntısı, KAP ek sayısı ve kaynak bağlantısı bulunur. Tam makaleler yeniden yayımlanmaz.
Telegram bağlantı ve büyük görsel önizlemesi açıktır.

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
NEWS_SOURCES=kap,bloomberght,investing,ntvpara,trthaber,tradingview
NEWS_LIMIT=100
PER_RUN_SEND_LIMIT=30
DETAIL_MAX_CHARS=1800
TELEGRAM_SEND_DELAY=4
```

## Cache ve ilk çalışma

Her kaynak `news_cache.json` içinde ayrı takip edilir. Yeni kaynak ilk çalışmada eski haberleri
göndermez. Bir kaynak hata verirse diğerleri çalışmaya devam eder ve başarısız kaynağın cache'i
ilerletilmez.

## Yerel test

```bash
pip install -r requirements.txt
python -m unittest -v test_news_bot.py test_news_sources.py
DRY_RUN=1 python news_bot.py
```

PowerShell:

```powershell
$env:DRY_RUN='1'
python news_bot.py
```
