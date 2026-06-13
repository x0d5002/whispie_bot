import os
import time
import json
import logging
import requests
from playwright.sync_api import sync_playwright

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

        # Sayfanın yüklenmesi için bekle
        page.wait_for_timeout(3000)

        # Tüm sayfa HTML'ini al
        html = page.content()
        page.close()

        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "html.parser")

        # Farklı seçicileri dene
        cards = (
            soup.select("div[class*='question']") or
            soup.select("div[class*='Question']") or
            soup.select("div[class*='card']") or
            soup.select("div[class*='Card']") or
            soup.select("article") or
            soup.select("li[class*='question']")
        )

        log.info("Bulunan kart sayısı: %d", len(cards))

        for card in cards:
            # Tüm text içeriğini al
            text = card.get_text(separator=" ", strip=True)
            if not text or len(text) < 5:
                continue

            # Benzersiz ID
            link_el = card.select_one("a[href]")
            q_id = link_el["href"] if link_el else str(hash(text[:100]))

            questions.append({"id": q_id, "text": text[:500], "time": ""})

        # Eğer kartlar bulunamadıysa tüm sayfadan p/span ile dene
        if not questions:
            log.warning("Kart bulunamadı, alternatif seçici deneniyor...")
            for el in soup.select("p, span[class*='question'], div[class*='content']"):
                text = el.get_text(strip=True)
                if text and len(text) > 10:
                    q_id = str(hash(text[:100]))
                    questions.append({"id": q_id, "text": text[:500], "time": ""})

    except Exception as e:
        log.error("Sayfa çekilemedi: %s", e)

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
    log.info("Daha önce görülen %d soru yüklendi.", len(seen))

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"]
        )

        while True:
            try:
                questions = fetch_questions(browser)
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
                    log.info("%d yeni soru bildirildi.", new_count)
                else:
                    log.info("Yeni soru yok.")

            except Exception as e:
                log.error("Beklenmeyen hata: %s", e)

            time.sleep(CHECK_INTERVAL)

        browser.close()

if __name__ == "__main__":
    main()
