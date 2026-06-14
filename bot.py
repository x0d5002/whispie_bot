import os
import time
import json
import logging
import requests
from playwright.sync_api import sync_playwright
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

def fetch_questions(browser) -> list[dict]:
    questions = []
    try:
        page = browser.new_page()
        page.set_extra_http_headers({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36"
        })
        log.info("Sayfa açılıyor: %s", WHISPI_URL)
        page.goto(WHISPI_URL, wait_until="networkidle", timeout=30000)
        page.wait_for_timeout(5000)

        html = page.content()
        page.close()

        # HTML yapısını debug için log'a yaz (ilk 3000 karakter)
        log.info("=== SAYFA HTML BAŞLANGIÇ ===")
        log.info(html[:3000])
        log.info("=== SAYFA HTML BİTİŞ ===")

        soup = BeautifulSoup(html, "html.parser")

        # Tüm div class isimlerini listele
        all_classes = set()
        for tag in soup.find_all(True):
            if tag.get("class"):
                for c in tag["class"]:
                    all_classes.add(c)
        log.info("Sayfadaki CSS sınıfları: %s", list(all_classes)[:50])

    except Exception as e:
        log.error("Sayfa çekilemedi: %s", e)

    return questions

def main():
    log.info("Bot başlatılıyor... Kullanıcı: %s", WHISPI_USERNAME)
    send_telegram(
        f"🤖 <b>Whispi Bot Aktif! (Debug Modu)</b>\n\n"
        f"📋 Profil: <a href='{WHISPI_URL}'>@{WHISPI_USERNAME}</a>\n"
        f"HTML yapısı inceleniyor, logları kontrol et..."
    )

    seen = load_seen()

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"]
        )

        # Sadece bir kez çalıştır (debug için)
        fetch_questions(browser)
        log.info("Debug tamamlandı. Logları kontrol et.")

        browser.close()

if __name__ == "__main__":
    main()
