# 🔔 Whispi → Telegram Bildirim Botu

whispi.io'ya yeni anonim soru geldiğinde Telegram'a anlık bildirim gönderir.

---

## 📋 Kurulum Adımları

### 1. Telegram Bot Token Al

1. Telegram'da **@BotFather**'a git
2. `/newbot` yaz
3. Bot adını gir (örn: `Whispi Bildirimlerim`)
4. Kullanıcı adını gir (örn: `whispi_benim_bot`)
5. Sana verilen **token**'ı kopyala → `TELEGRAM_TOKEN`

---

### 2. Telegram Chat ID'ni Al

1. Telegram'da **@userinfobot**'a git
2. `/start` yaz
3. Sana verilen **Id** numarasını kopyala → `TELEGRAM_CHAT_ID`

---

### 3. Railway'e Deploy Et (Ücretsiz)

1. [railway.app](https://railway.app) sitesine git, GitHub ile giriş yap
2. **"New Project" → "Deploy from GitHub repo"** seç
3. Bu klasörü GitHub'a yükle (ya da zip olarak Railway'e ver)
4. **Variables** sekmesine gir ve şunları ekle:

```
TELEGRAM_TOKEN     = BotFather'dan aldığın token
TELEGRAM_CHAT_ID   = @userinfobot'tan aldığın id
WHISPI_USERNAME    = whispi.io kullanıcı adın (@ olmadan)
CHECK_INTERVAL     = 60
```

5. **Deploy** butonuna bas — bot 7/24 çalışmaya başlar!

---

## 🧪 Yerel Test (İsteğe Bağlı)

```bash
# Gerekli paketleri kur
pip install -r requirements.txt

# Ortam değişkenlerini ayarla
export TELEGRAM_TOKEN="token_buraya"
export TELEGRAM_CHAT_ID="chat_id_buraya"
export WHISPI_USERNAME="kullanici_adin"

# Botu çalıştır
python bot.py
```

---

## ⚙️ Nasıl Çalışır?

- Bot her **60 saniyede** bir whispi.io profilini kontrol eder
- Yeni soru varsa Telegram'a şu formatta mesaj gönderir:

```
📩 Yeni Anonim Soru!

❓ [Soru metni]

👉 Cevaplamak için tıkla
```

- Daha önce görülen sorular tekrar bildirilmez
- Bot başlatıldığında aktivasyon mesajı gönderir

---

## 🛠 Dosya Yapısı

```
whispi-telegram-bot/
├── bot.py            # Ana bot kodu
├── requirements.txt  # Python bağımlılıkları
├── Dockerfile        # Railway için container tanımı
├── .env.example      # Değişken şablonu
└── README.md         # Bu dosya
```
