import os
import asyncio
import yt_dlp
from pydub import AudioSegment
from shazamio import Shazam
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
)

# ================= SOZLAMALAR =================
TELEGRAM_TOKEN = "8522396515:AAHNjZBxPTas3YkrPrpcp498XlZMY8x9ckY"
MY_TG = "@Rustamov_v1"
MY_IG = "@bahrombekh_fx"
# ==============================================

# YouTube cache
yt_cache = {}  # {index: video_url}

# Instagram videolarni vaqtincha saqlash
insta_videos = {}  # {chat_id: video_file_path}

# ================= /start KOMANDASI =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        f"👋 Salom! Men musiqa topuvchi botman 🎵\n\n"
        f"👤 Telegram: {MY_TG}\n"
        f"📸 Instagram: {MY_IG}\n\n"
        "Menga qo‘shiq nomi yozing yoki Instagram link tashlang 🎧"
    )
    await update.message.reply_text(text)

# ================= YOUTUBE QIDIRUV + PAGINATION =================
async def search_youtube_paginated(update: Update, query: str, page: int = 0):
    search_url = f"ytsearch20:{query} official audio"
    ydl_opts = {
        "format": "bestaudio/best",
        "quiet": True,
        "cookies": "cookies.txt"  # cookies faylini bot papkasiga qo'ying
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(search_url, download=False)
            entries = info.get("entries", [])
            if not entries:
                await update.message.reply_text("🔍 Natija topilmadi.")
                return

            per_page = 5
            start = page * per_page
            end = start + per_page
            current_entries = entries[start:end]

            keyboard = []
            for idx, e in enumerate(current_entries, start=start+1):
                title = e.get("title", "No title")[:50]
                url = e.get("webpage_url")
                yt_cache[idx] = url
                keyboard.append([InlineKeyboardButton(f"{idx}. {title}", callback_data=f"yt|{idx}")])

            nav_buttons = []
            if start > 0:
                nav_buttons.append(InlineKeyboardButton("⬅️", callback_data=f"page|{page-1}|{query}"))
            if end < len(entries):
                nav_buttons.append(InlineKeyboardButton("➡️", callback_data=f"page|{page+1}|{query}"))
            if nav_buttons:
                keyboard.append(nav_buttons)

            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text("🎧 Tanlang:", reply_markup=reply_markup)

    except Exception as e:
        await update.message.reply_text(f"❌ YouTube xatosi: {e}")

# ================= CALLBACK HANDLER =================
async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data.startswith("yt|"):
        vid_id = int(data.split("|")[1])
        await download_and_send_youtube(update, vid_id)
    elif data.startswith("page|"):
        _, page, query_text = data.split("|", 2)
        await search_youtube_paginated(update, query_text, int(page))
        await query.message.delete()  # eski xabarni o‘chirish

# ================= YOUTUBE QIDIRUV =================
async def search_youtube(update: Update, query: str):
    search_url = f"ytsearch5:{query} official audio"
    ydl_opts = {
        "format": "bestaudio/best",
        "quiet": True,
        "cookies": "cookies.txt"
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(search_url, download=False)
            entries = info.get("entries", [])[:5]

            if not entries:
                await update.message.reply_text("🔍 Natija topilmadi.")
                return

            keyboard = []
            for idx, e in enumerate(entries, start=1):
                title = e.get("title", "No title")[:60]
                url = e.get("webpage_url")
                yt_cache[idx] = url
                keyboard.append([InlineKeyboardButton(f"{idx}. {title}", callback_data=f"yt|{idx}")])

            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text("🎧 Quyidagi videolardan birini tanlang:", reply_markup=reply_markup)

    except Exception as e:
        await update.message.reply_text(f"❌ YouTube xatosi: {e}")

# ================= YOUTUBE MP3 YUKLASH =================
async def download_and_send_youtube(update: Update, vid_id: int):
    url = yt_cache.get(vid_id)
    if not url:
        await update.callback_query.message.reply_text("⚠️ Video topilmadi.")
        return

    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": "song_temp.%(ext)s",
        "quiet": True,
        "cookies": "cookies.txt",
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192",
        }],
    }

    await update.callback_query.edit_message_text("⏳ Yuklanmoqda...")

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            fname = f"song_temp.{info.get('ext', 'mp3')}"

        # Telegramga yuborish
        await update.effective_chat.send_audio(
            audio=open(fname, "rb"),
            caption=f"🎶 {info.get('title', '')}"
        )

    except Exception as e:
        await update.effective_chat.send_message(f"⚠️ Yuklab bo‘lmadi: {e}")

    finally:
        if os.path.exists(fname):
            os.remove(fname)

# ================= ASOSIY HANDLER =================
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()

    if "instagram.com" in text:
        await download_instagram(update, text)
    elif "youtube.com" in text or "youtu.be" in text:
        yt_cache[0] = text
        await download_and_send_youtube(update, 0)
    else:
        await update.message.reply_text("🎧 Musiqa qidirilmoqda...")
        await search_youtube(update, text)

# ================= BOTNI ISHGA TUSHURISH =================
def build_app():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(callback_handler))
    return app

if __name__ == "__main__":
    app = build_app()
    print("🤖 Bot ishga tushdi...")
    asyncio.run(app.run_polling())
