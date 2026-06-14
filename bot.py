import os
import time
import json
import logging
import requests
from bs4 import BeautifulSoup

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)

TELEGRAM_TOKEN   = os.environ["TELEGRAM_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
WHISPI_USERNAME  = os.environ["WHISPI_USERNAME"].lstrip("@/").strip()
CHECK_INTERVAL   = int(os.getenv("CHECK_INTERVAL", "60"))

WHISPI_URL = f"https://whispi.io/@/{WHISPI_USERNAME}"
STATE_FILE = "seen_questions.json"

def load_seen() -> set:
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            return set(json.load(f))
    return set()

def save_seen(seen: set):
    with open(STATE_FILE, "w") as f:
        json.dump(list(seen), f)

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

def fetch_questions() -> list[dict]:
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36"
    }
    try:
        resp = requests.get(WHISPI_URL, headers=headers, timeout=15)
        resp.raise_for_status()
    except requests.RequestException as e:
        log.error("whispi.io isteği başarısız: %s", e)
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    questions = []

    for card in soup.select("div, article, li"):
        text = card.get_text(separator=" ", strip=True)
        if text and 10 < len(text) < 500:
            q_id = str(hash(text[:100]))
            questions.append({"id": q_id, "text": text})

    log.info("%d soru bulundu.", len(questions))
    return questions

def main():
    log.info("Bot başlatılıyor... Kullanıcı: %s", WHISPI_USERNAME)
    send_telegram(
        f"🤖 <b>Whispi Bot Aktif!</b>\n\n"
        f"📋 Profil: <a href='{WHISPI_URL}'>@{WHISPI_USERNAME}</a>\n"
        f"⏱ Kontrol aralığı: her {CHECK_INTERVAL} saniye\n\n"
        f"Yeni sorular geldiğinde buraya bildirim alacaksın. 🔔"
    )

    seen = load_seen()

    while True:
        try:
            questions = fetch_questions()
            new_count = 0

            for q in questions:
                if q["id"] not in seen:
                    seen.add(q["id"])
                    new_count += 1
                    msg = (
                        f"📩 <b>Yeni Anonim Soru!</b>\n\n"
                        f"❓ {q['text']}\n\n"
                        f"👉 <a href='{WHISPI_URL}'>Cevaplamak için tıkla</a>"
                    )
                    send_telegram(msg)
                    time.sleep(1)

            if new_count:
                save_seen(seen)
            else:
                log.info("Yeni soru yok.")

        except Exception as e:
            log.error("Beklenmeyen hata: %s", e)

        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()