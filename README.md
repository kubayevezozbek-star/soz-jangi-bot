# ⚔️ So'z Jangi — Telegram Multiplayer Bot & Mini App

Ushbu bot 96 kunlik (4 915 ta so'zdan iborat) ingliz tili lug'atlari asosida ishlovchi real-time multiplayer "So'z Jangi" (Word Battle) o'yinidir.

---

## 🎯 Asosiy Imkoniyatlar:
1. **Rejimlar:**
   - ⚡ **Solo (1 o'zim):** O'z bilimini sinash va mashq qilish.
   - ⚔️ **Multiplayer (2, 3, 4, 5, 6 kishilik xonalar):** Do'stlar bilan jonli bellashuv.
2. **Xona va Havola tizimi:**
   - Xona ochuvchi xonadagi o'yinchilar sonini va qaysi kun lug'atidan (1-dan 96-kungacha) o'ynashni tanlaydi.
   - 6 xonali maxsus kod va Telegram taklif havolasi (`t.me/soz_jangi_bot?start=room_XXXXXX`) yaratiladi.
   - Barcha o'yinchilar ulanib, "Boshlash" bosilganda bellashuv start oladi.
3. **Savollar va Vaqt:**
   - **4 talik Test savoli:** ⏱️ 10 soniya (chalg'ituvchi variantlar bilan).
   - **Yozma savol:** ⏱️ 20 soniya (so'zning tarjimasini kiritish).
   - *Agar hamma javob berib bo'lsa, vaqt tugashini kutmasdan avtomatik keyingi savolga o'tiladi.*
4. **Ballar va Xatolar:**
   - 1-bo'lib to'g'ri topganga: **+5 ball**
   - 2-bo'lib: **+4 ball**, 3-chiga: **+3 ball**, 4-chiga: **+2 ball**, 5-6: **+1 ball**
   - Noto'g'ri javob berganga: **-1 ball jarima**
   - Javob berilishi bilanoq to'g'ri javob darhol ko'rsatiladi.
   - O'yin so'ngida 1-, 2-, 3-o'rinlar shohsupasi va yo'l qo'yilgan xatolar ro'yxati chiqadi.
5. **Mini App va Chat interfeysi:**
   - O'yin ham zamonaviy **Telegram Mini App (Web App)** orqali, ham to'g'ridan-to'g'ri **Telegram chatida (Inline tugmalar)** sinxron ishlaydi!

---

## 📁 Loyiha Tuzilishi:
```
soz_jangi_bot/
│
├── data/
│   ├── raw_vocab.txt          # 1-kundan 96-kungacha xom lug'at matni
│   ├── words.json             # To'liq tozalangan va indekslangan lug'at (4915 ta so'z)
│   └── soz_jangi.db           # SQLite ma'lumotlar bazasi (avtomatik yaratiladi)
│
├── handlers/
│   └── bot_handlers.py        # Telegram bot komandalari va xabarlar
│
├── web/
│   ├── templates/
│   │   └── index.html         # Zamonaviy Telegram Mini App interfeysi (Audio sintezator, timer, animatsiyalar)
│   └── static/
│
├── config.py                  # Sozlamalar va tokenlar
├── database.py                # Foydalanuvchilar va o'yinlar statistikasi
├── game_engine.py             # Jonli xonalar va multiplayer o'yin mexanikasi
├── vocab_manager.py           # 96 kunlik lug'at va savollar generatori
├── web_server.py              # aiohttp Web server va WebSockets
├── main.py                    # Asosiy ishga tushiruvchi fayl
├── requirements.txt           # Kerakli kutubxonalar
├── Procfile                   # Cloud (Render, Railway) uchun
├── render.yaml                # Render 1-click deploy konfiguratsiyasi
├── run.bat                    # Noutbukda 1-bosishda ishga tushirish skripti
└── .env                       # Token va admin sozlamalari
```

---

## 🚀 Ishga Tushirish:

### 1. Noutbukingizda lokal ishga tushirish:
Loyiha papkasidagi **`run.bat`** faylini sichqoncha bilan 2 marta bosing. Virtual muhit avtomatik ishga tushadi va bot faollashadi!

Yoki PowerShell orqali:
```powershell
cd C:\Users\User\.gemini\antigravity\scratch\soz_jangi_bot
.\.venv\Scripts\python.exe main.py
```

### 2. 24/7 Ishlaydigan qilib bepul serverga (Render.com) joylash:
1. GitHub-da yangi shaxsiy (private yoki public) repozitoriy oching.
2. Ushbu papkadagi fayllarni GitHub-ga yuklang.
3. [Render.com](https://render.com) ga kiring va **New Web Service** tugmasini bosing.
4. Repozitoriyingizni tanlang:
   - **Environment:** Python
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `python main.py`
5. **Environment Variables** bo'limida qo'shing:
   - `BOT_TOKEN`: `9056051300:AAHr9MglvV6lhk_JrR86_CSvr-TwjhWdOq8`
   - `ADMIN_ID`: `1438313297`
   - `PORT`: `10000`
   - `WEBAPP_URL`: Render sizga beradigan domen (masalan: `https://soz-jangi-bot.onrender.com`)
6. **Deploy** ni bosing! Bot serverda 24/7 to'xtovsiz ishlaydi!
