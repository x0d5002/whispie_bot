import os
import time
import json
import logging
import requests
from bs4 import BeautifulSoup
from datetime import datetime

# ── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)

# ── Config (ortam değişkenlerinden okunur) ────────────────────────────────────
TELEGRAM_TOKEN   = os.environ["TELEGRAM_TOKEN"]    # BotFather'dan alınan token
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]  # Senin chat id'n
WHISPI_USERNAME  = os.environ["WHISPI_USERNAME"]   # whispi.io kullanıcı adın
CHECK_INTERVAL   = int(os.getenv("CHECK_INTERVAL", "60"))  # saniye (varsayılan 60)

WHISPI_URL = f"https://whispi.io/{WHISPI_USERNAME}"
STATE_FILE = "seen_questions.json"

# ── Durum dosyası ─────────────────────────────────────────────────────────────

def load_seen() -> set:
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            return set(json.load(f))
    return set()

def save_seen(seen: set):
    with open(STATE_FILE, "w") as f:
        json.dump(list(seen), f)

# ── Telegram mesaj gönder ─────────────────────────────────────────────────────

def send_telegram(text: str):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }
    resp = requests.post(url, json=payload, timeout=10)
    if not resp.ok:
        log.error("Telegram gönderilemedi: %s", resp.text)
    else:
        log.info("Telegram mesajı gönderildi.")

# ── whispi.io scrape ──────────────────────────────────────────────────────────

def fetch_questions() -> list[dict]:
    """
    whispi.io/{username} sayfasındaki soruları çeker.
    Her soru: { "id": str, "text": str, "time": str }
    """
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0 Safari/537.36"
        )
    }
    try:
        resp = requests.get(WHISPI_URL, headers=headers, timeout=15)
        resp.raise_for_status()
    except requests.RequestException as e:
        log.error("whispi.io isteği başarısız: %s", e)
        return []

    soup = BeautifulSoup(resp.text, "html.parser")

    questions = []

    # whispi.io'nun HTML yapısına göre soru kartlarını bul
    # Olası seçici kombinasyonları dene
    cards = (
        soup.select("div.question-card")
        or soup.select("div[class*='question']")
        or soup.select("article")
        or soup.select("div.card")
    )

    for card in cards:
        # Soru metnini al
        text_el = (
            card.select_one("p.question-text")
            or card.select_one("p")
            or card.select_one("span.text")
            or card.select_one("[class*='text']")
        )
        if not text_el:
            continue

        text = text_el.get_text(strip=True)
        if not text:
            continue

        # Benzersiz id üret (href veya içerik hash'i)
        link_el = card.select_one("a[href]")
        q_id = link_el["href"] if link_el else str(hash(text))

        # Zaman bilgisi (varsa)
        time_el = card.select_one("time") or card.select_one("[class*='time']") or card.select_one("[class*='date']")
        q_time  = time_el.get_text(strip=True) if time_el else ""

        questions.append({"id": q_id, "text": text, "time": q_time})

    log.info("%d soru bulundu.", len(questions))
    return questions

# ── Ana döngü ─────────────────────────────────────────────────────────────────

def main():
    log.info("Bot başlatılıyor... Kullanıcı: @%s", WHISPI_USERNAME)
    send_telegram(
        f"🤖 <b>Whispi Bot Aktif!</b>\n\n"
        f"📋 Profil: <a href='{WHISPI_URL}'>{WHISPI_USERNAME}</a>\n"
        f"⏱ Kontrol aralığı: her {CHECK_INTERVAL} saniye\n\n"
        f"Yeni sorular geldiğinde buraya bildirim alacaksın. 🔔"
    )

    seen = load_seen()
    log.info("Daha önce görülen %d soru yüklendi.", len(seen))

    while True:
        try:
            questions = fetch_questions()
            new_count = 0

            for q in questions:
                if q["id"] not in seen:
                    seen.add(q["id"])
                    new_count += 1

                    time_str = f"\n🕐 {q['time']}" if q["time"] else ""
                    msg = (
                        f"📩 <b>Yeni Anonim Soru!</b>{time_str}\n\n"
                        f"❓ {q['text']}\n\n"
                        f"👉 <a href='{WHISPI_URL}'>Cevaplamak için tıkla</a>"
                    )
                    send_telegram(msg)
                    time.sleep(1)  # Telegram rate limit

            if new_count:
                save_seen(seen)
                log.info("%d yeni soru bildirildi.", new_count)
            else:
                log.info("Yeni soru yok.")

        except Exception as e:
            log.error("Beklenmeyen hata: %s", e)

        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()
