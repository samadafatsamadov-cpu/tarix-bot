import subprocess
import sys
subprocess.check_call([sys.executable, "-m", "pip", "install", "--break-system-packages", "requests", "schedule"])

import requests
import schedule
import time
import json
import os
from datetime import datetime

BOT_TOKEN = "8908020561:AAHA52gPEwUXeO0a0kskG7NtxIaY6jYrCc8"
GEMINI_API_KEY = "AQ.Ab8RN6JAPbEVkD8u-mXjWTZdjUR7famIZmOknGZUo3EYT6olpg"
# İstifadəçiləri saxlayan fayl
USERS_FILE = "users.json"

def istifadecileri_yukle():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, "r") as f:
            return json.load(f)
    return []

def istifadeci_saxla(chat_id):
    users = istifadecileri_yukle()
    if chat_id not in users:
        users.append(chat_id)
        with open(USERS_FILE, "w") as f:
            json.dump(users, f)
        print(f"✅ Yeni istifadəçi: {chat_id}")

def ay_adi(ay):
    aylar = {
        1: "Yanvar", 2: "Fevral", 3: "Mart", 4: "Aprel",
        5: "May", 6: "İyun", 7: "İyul", 8: "Avqust",
        9: "Sentyabr", 10: "Oktyabr", 11: "Noyabr", 12: "Dekabr"
    }
    return aylar.get(ay, "")

def fakt_metni_hazirla():
    bugun = datetime.now()
    ay = bugun.month
    gun = bugun.day

    wiki_url = f"https://en.wikipedia.org/api/rest_v1/feed/onthisday/events/{ay}/{gun}"
    wiki_response = requests.get(wiki_url)
    wiki_data = wiki_response.json()

    hadiseler = wiki_data.get("events", [])[:10]
    hadise_metni = ""
    for h in hadiseler:
        il = h.get("year", "")
        metn = h.get("text", "")
        hadise_metni += f"{il}: {metn}\n"

    prompt = f"""
Aşağıda {gun} {ay_adi(ay)} tarixində tarixdə baş vermiş hadisələr var (ingiliscə).
Ən maraqlı və məşhur 3-ünü seç, Azərbaycan dilinə tərcümə et.

Cavabı YALNIZ belə formatda ver, başqa heç nə yazma:
🗓 *Tarixdə bu gün — {gun} {ay_adi(ay)}*

1️⃣ *[İl]* — [Hadisə]

2️⃣ *[İl]* — [Hadisə]

3️⃣ *[İl]* — [Hadisə]

Hadisələr:
{hadise_metni}
"""

    gemini_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}"
    gemini_response = requests.post(
        gemini_url,
        json={"contents": [{"parts": [{"text": prompt}]}]}
    )
    return gemini_response.json()["candidates"][0]["content"]["parts"][0]["text"]

def hamiya_gonder():
    try:
        users = istifadecileri_yukle()
        if not users:
            print("⚠️ Heç bir istifadəçi yoxdur hələ")
            return

        metn = fakt_metni_hazirla()

        for chat_id in users:
            requests.post(
                f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                json={
                    "chat_id": chat_id,
                    "text": metn,
                    "parse_mode": "Markdown"
                }
            )
            print(f"✅ Göndərildi: {chat_id}")

    except Exception as e:
        print(f"❌ Xəta: {e}")

def yeni_istifadecileri_yoxla():
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates"
        response = requests.get(url)
        updates = response.json().get("result", [])

        for update in updates:
            message = update.get("message", {})
            text = message.get("text", "")
            chat_id = message.get("chat", {}).get("id")

            if text == "/start" and chat_id:
                istifadeci_saxla(chat_id)
                # Xoş gəldin mesajı göndər
                requests.post(
                    f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                    json={
                        "chat_id": chat_id,
                        "text": "👋 Salam! Hər gün səhər saat 10:00-da tarixdə bu günə aid 3 maraqlı fakt göndərəcəyəm!",
                        "parse_mode": "Markdown"
                    }
                )

        # Oxunmuş mesajları işarələ
        if updates:
            last_id = updates[-1]["update_id"]
            requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates?offset={last_id+1}")

    except Exception as e:
        print(f"❌ Yoxlama xətası: {e}")

# Hər gün saat 10:00-da göndər
schedule.every().day.at("10:00").do(hamiya_gonder)

# Hər 5 saniyədə yeni istifadəçiləri yoxla
schedule.every(5).seconds.do(yeni_istifadecileri_yoxla)

print("🤖 Bot işə düşdü!")
print("📌 İstifadəçilər /start göndərəndə avtomatik qeydiyyatdan keçəcək")

while True:
    schedule.run_pending()
    time.sleep(1)
