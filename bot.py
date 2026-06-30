"""
🤖 TeleDownloader Pro Bot
Features: Queue system, Plans (Free/Paid), Ads, Multi-format download
"""

import os
import asyncio
import logging
import json
import time
from datetime import datetime, timedelta
from collections import deque
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup
)
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    CallbackQueryHandler, filters, ContextTypes
)
import yt_dlp

from config import BOT_TOKEN, ADMIN_IDS
from database import Database
from plans import PlanManager
from queue_manager import DownloadQueue

# ── Logging ──────────────────────────────────────────────────────────────────
os.makedirs("logs", exist_ok=True)
os.makedirs("downloads", exist_ok=True)
os.makedirs("data", exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("logs/bot.log"),
        logging.StreamHandler()
    ]
)
log = logging.getLogger(__name__)

# ── Init ──────────────────────────────────────────────────────────────────────
db = Database()
plan_mgr = PlanManager(db)
dl_queue = DownloadQueue()

os.makedirs("downloads", exist_ok=True)
os.makedirs("logs", exist_ok=True)

# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def main_menu_keyboard(user_id: int):
    plan = db.get_user_plan(user_id)
    plan_label = "⭐ Premium" if plan == "premium" else "🆓 Free"
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📥 How to Download", callback_data="help_download")],
        [InlineKeyboardButton(f"💳 My Plan ({plan_label})", callback_data="my_plan"),
         InlineKeyboardButton("🚀 Upgrade", callback_data="upgrade")],
        [InlineKeyboardButton("📊 My Stats", callback_data="my_stats"),
         InlineKeyboardButton("ℹ️ About", callback_data="about")],
    ])

async def send_ad(update: Update, context: ContextTypes.DEFAULT_TYPE, seconds: int = 10):
    """Show a 10-second ad with countdown, then auto-delete."""
    ads = [
        "🌟 **AD** |contact me for Ads darshanmalewar682@gmail.com",
        "💡 **AD** | contact me for Ads darshanmalewar682@gmail.com",
        "🎵 **AD** |contact me for Ads darshanmalewar682@gmail.com",
        "📱 **AD** |contact me for Ads darshanmalewar682@gmail.com",
    ]
    import random
    ad_text = random.choice(ads)

    msg = await update.effective_message.reply_text(
        f"{ad_text}\n\n⏳ Your download starts in **{seconds}s**...",
        parse_mode="Markdown"
    )

    for i in range(seconds - 1, 0, -1):
        await asyncio.sleep(1)
        try:
            await msg.edit_text(
                f"{ad_text}\n\n⏳ Your download starts in **{i}s**...",
                parse_mode="Markdown"
            )
        except Exception:
            pass

    await asyncio.sleep(1)
    try:
        await msg.delete()
    except Exception:
        pass

# ─────────────────────────────────────────────────────────────────────────────
# COMMANDS
# ─────────────────────────────────────────────────────────────────────────────

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db.add_user(user.id, user.username or user.first_name)
    log.info(f"User started: {user.id} (@{user.username})")

    text = (
        f"👋 Welcome, **{user.first_name}**!\n\n"
        "I'm **TeleDownloader Pro** 🚀\n"
        "Send me any link to download:\n"
        "🎥 Videos • 🎵 Music • 🖼 Photos • 📄 Files\n\n"
        "Supports **1000+ sites** including YouTube, Instagram,\n"
        "TikTok, Twitter, Facebook, Reddit & more!\n\n"
        "👇 Use the menu below or just paste a link!"
    )
    await update.message.reply_text(
        text, parse_mode="Markdown",
        reply_markup=main_menu_keyboard(user.id)
    )

async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "📖 **How to use:**\n\n"
        "1️⃣ Just paste any link\n"
        "2️⃣ Choose format (Video/Audio/Photo)\n"
        "3️⃣ Wait for download ✅\n\n"
        "**Commands:**\n"
        "/start — Main menu\n"
        "/plan — View your plan\n"
        "/upgrade — Upgrade to Premium\n"
        "/stats — Your download stats\n"
        "/queue — Check queue position\n"
        "/cancel — Cancel current download\n\n"
        "**Supported sites:**\n"
        "YouTube, Instagram, TikTok, Twitter/X,\n"
        "Facebook, Reddit, SoundCloud, Vimeo,\n"
        "Dailymotion, Pinterest & 1000+ more!"
    )
    await update.message.reply_text(text, parse_mode="Markdown")

async def cmd_plan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    plan = db.get_user_plan(user_id)
    stats = db.get_user_stats(user_id)
    limit = plan_mgr.daily_limit(plan)
    today = stats.get("today", 0)

    text = (
        f"💳 **Your Plan: {'⭐ Premium' if plan == 'premium' else '🆓 Free'}**\n\n"
        f"📥 Downloads today: `{today}` / `{'∞' if limit == -1 else limit}`\n"
        f"📦 Max file size: `{'10000 GB' if plan == 'premium' else '75 MB'}`\n"
        f"⚡ Queue priority: `{'HIGH' if plan == 'premium' else 'Normal'}`\n"
        f"🚫 Ads: `{'None ✅' if plan == 'premium' else '10s per download'}`\n"
        f"🎵 MP3 quality: `{'320kbps' if plan == 'premium' else '128kbps'}`\n"
        f"📂 Batch links: `{'Yes (up to 5)' if plan == 'premium' else 'No'}`\n"
    )
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🚀 Upgrade to Premium", callback_data="upgrade")],
        [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")],
    ])
    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=kb)

async def cmd_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    stats = db.get_user_stats(user_id)
    text = (
        "📊 **Your Stats:**\n\n"
        f"📥 Total downloads: `{stats.get('total', 0)}`\n"
        f"🎥 Videos: `{stats.get('video', 0)}`\n"
        f"🎵 Audio: `{stats.get('audio', 0)}`\n"
        f"🖼 Photos: `{stats.get('photo', 0)}`\n"
        f"📅 Downloads today: `{stats.get('today', 0)}`\n"
        f"💾 Data downloaded: `{stats.get('data_mb', 0):.1f} MB`\n"
    )
    await update.message.reply_text(text, parse_mode="Markdown")

async def cmd_queue(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    pos = dl_queue.position(user_id)
    size = dl_queue.size()
    if pos == 0:
        await update.message.reply_text("✅ You have no active download in queue.")
    else:
        await update.message.reply_text(
            f"📋 **Queue Status:**\n\n"
            f"Your position: `#{pos}`\n"
            f"Total in queue: `{size}`\n"
            f"Est. wait: `~{pos * 30}s`",
            parse_mode="Markdown"
        )

async def cmd_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    removed = dl_queue.remove(user_id)
    if removed:
        await update.message.reply_text("🚫 Download cancelled.")
    else:
        await update.message.reply_text("ℹ️ No active download to cancel.")

async def cmd_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return
    stats = db.get_global_stats()
    text = (
        "🔧 **Admin Panel**\n\n"
        f"👥 Total users: `{stats['users']}`\n"
        f"⭐ Premium users: `{stats['premium']}`\n"
        f"📥 Total downloads: `{stats['downloads']}`\n"
        f"📋 Queue size: `{dl_queue.size()}`\n\n"
        "Commands:\n"
        "`/grant <user_id>` — Grant premium\n"
        "`/revoke <user_id>` — Revoke premium\n"
        "`/broadcast <msg>` — Message all users"
    )
    await update.message.reply_text(text, parse_mode="Markdown")

async def cmd_grant(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return
    if not context.args:
        await update.message.reply_text("Usage: /grant <user_id>")
        return
    uid = int(context.args[0])
    db.set_plan(uid, "premium")
    await update.message.reply_text(f"✅ Premium granted to `{uid}`", parse_mode="Markdown")

async def cmd_revoke(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return
    if not context.args:
        await update.message.reply_text("Usage: /revoke <user_id>")
        return
    uid = int(context.args[0])
    db.set_plan(uid, "free")
    await update.message.reply_text(f"✅ Plan revoked for `{uid}`", parse_mode="Markdown")

# ─────────────────────────────────────────────────────────────────────────────
# LINK HANDLER
# ─────────────────────────────────────────────────────────────────────────────

async def handle_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    url = update.message.text.strip()

    # Validate URL
    if not (url.startswith("http://") or url.startswith("https://")):
        await update.message.reply_text(
            "❌ Please send a valid URL starting with http:// or https://"
        )
        return

    plan = db.get_user_plan(user_id)

    # Check daily limit
    if not plan_mgr.can_download(user_id, plan):
        limit = plan_mgr.daily_limit(plan)
        await update.message.reply_text(
            f"⛔ **Daily limit reached!**\n\n"
            f"Free plan allows `{limit}` downloads/day.\n"
            f"Upgrade to Premium for unlimited downloads! 🚀",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🚀 Upgrade Now", callback_data="upgrade")]
            ])
        )
        return

    # Store URL for callback
    context.user_data["pending_url"] = url

    # Ask format
    kb = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🎥 Video (MP4)", callback_data="fmt_video"),
            InlineKeyboardButton("🎵 Audio (MP3)", callback_data="fmt_audio"),
        ],
        [
            InlineKeyboardButton("🖼 Photo/Image", callback_data="fmt_photo"),
            InlineKeyboardButton("📄 Best Quality", callback_data="fmt_best"),
        ],
        [InlineKeyboardButton("❌ Cancel", callback_data="cancel_dl")]
    ])
    await update.message.reply_text(
        f"🔗 Link detected!\n`{url[:60]}{'...' if len(url)>60 else ''}`\n\n"
        "Choose download format:",
        parse_mode="Markdown",
        reply_markup=kb
    )

# ─────────────────────────────────────────────────────────────────────────────
# CALLBACK HANDLER
# ─────────────────────────────────────────────────────────────────────────────

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = update.effective_user.id

    # ── Navigation ────────────────────────────────────────────────────────────
    if data == "main_menu":
        await query.edit_message_text(
            "🏠 **Main Menu** — Paste any link to start!",
            parse_mode="Markdown",
            reply_markup=main_menu_keyboard(user_id)
        )

    elif data == "help_download":
        await query.edit_message_text(
            "📖 **How to Download:**\n\n"
            "1️⃣ Copy any video/audio/image link\n"
            "2️⃣ Paste it in this chat\n"
            "3️⃣ Choose your format\n"
            "4️⃣ Wait a moment ✅\n\n"
            "Works with YouTube, Instagram, TikTok,\n"
            "Twitter, Facebook, Reddit & 1000+ sites!",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🏠 Back", callback_data="main_menu")]
            ])
        )

    elif data == "my_plan":
        plan = db.get_user_plan(user_id)
        stats = db.get_user_stats(user_id)
        limit = plan_mgr.daily_limit(plan)
        await query.edit_message_text(
            f"💳 **Your Plan: {'⭐ Premium' if plan == 'premium' else '🆓 Free'}**\n\n"
            f"📥 Today: `{stats.get('today',0)}` / `{'∞' if limit==-1 else limit}`\n"
            f"📦 Max size: `{'2 GB' if plan=='premium' else '50 MB'}`\n"
            f"🚫 Ads: `{'No ads ✅' if plan=='premium' else '10s per download'}`\n"
            f"🎵 MP3: `{'320kbps' if plan=='premium' else '128kbps'}`",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🚀 Upgrade", callback_data="upgrade")],
                [InlineKeyboardButton("🏠 Back", callback_data="main_menu")],
            ])
        )

    elif data == "my_stats":
        stats = db.get_user_stats(user_id)
        await query.edit_message_text(
            f"📊 **Your Stats:**\n\n"
            f"📥 Total: `{stats.get('total',0)}`\n"
            f"🎥 Videos: `{stats.get('video',0)}`\n"
            f"🎵 Audio: `{stats.get('audio',0)}`\n"
            f"🖼 Photos: `{stats.get('photo',0)}`\n"
            f"💾 Data: `{stats.get('data_mb',0):.1f} MB`",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🏠 Back", callback_data="main_menu")]
            ])
        )

    elif data == "about":
        await query.edit_message_text(
            "ℹ️ **TeleDownloader Pro**\n\n"
            "Version: 2.0\n"
            "Powered by yt-dlp\n"
            "Supports 1000+ sites\n\n"
            "Built with ❤️ using python-telegram-bot",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🏠 Back", callback_data="main_menu")]
            ])
        )

    elif data == "upgrade":
        await query.edit_message_text(
            "🚀 **Upgrade to Premium**\n\n"
            "**Free Plan:**\n"
            "• 5 downloads/day\n"
            "• Max 50 MB per file\n"
            "• 128kbps audio\n"
            "• 10s ads\n"
            "• Normal queue priority\n\n"
            "**⭐ Premium Plan — $4.99/month:**\n"
            "• ♾️ Unlimited downloads\n"
            "• Max 10000 GB per file\n"
            "• 320kbps audio\n"
            "• ✅ No ads ever\n"
            "• ⚡ Priority queue\n"
            "• 📂 Batch download (5 links at once)\n"
            "• 📌 Download history\n\n"
            "To upgrade, pay via the link below\n"
            "then send proof to the admin:",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("💳 Pay Now (Stripe)", url="https://buy.stripe.com/your_link")],
                [InlineKeyboardButton("💬 Contact Admin", url="https://t.me/your_admin_username")],
                [InlineKeyboardButton("🏠 Back", callback_data="main_menu")],
            ])
        )

    # ── Download Format Selection ─────────────────────────────────────────────
    elif data.startswith("fmt_"):
        fmt = data.replace("fmt_", "")
        url = context.user_data.get("pending_url")
        if not url:
            await query.edit_message_text("❌ No URL found. Please paste the link again.")
            return

        await query.edit_message_text(f"📋 Added to queue... ⏳")

        # Queue the download
        plan = db.get_user_plan(user_id)
        priority = 0 if plan == "premium" else 1
        await dl_queue.add(user_id, url, fmt, update, context, priority)

    elif data == "cancel_dl":
        context.user_data.pop("pending_url", None)
        await query.edit_message_text("🚫 Cancelled.")

# ─────────────────────────────────────────────────────────────────────────────
# DOWNLOAD WORKER
# ─────────────────────────────────────────────────────────────────────────────

async def process_download(user_id: int, url: str, fmt: str,
                           update: Update, context: ContextTypes.DEFAULT_TYPE):
    plan = db.get_user_plan(user_id)
    msg = await update.effective_message.reply_text("⏳ Starting download...")

    # Show ad for free users
    if plan != "premium":
        await send_ad(update, context, seconds=10)

    try:
        await msg.edit_text("🔄 Fetching info...")

        # Build yt-dlp options by format
        max_size = 2000 if plan == "premium" else 50  # MB
        audio_quality = "0" if plan == "premium" else "5"  # 0=best, 5~128k

        if fmt == "audio":
            ydl_opts = {
                'format': 'bestaudio/best',
                'outtmpl': f'downloads/{user_id}_%(title)s.%(ext)s',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': audio_quality,
                }],
                'quiet': True,
            }
        elif fmt == "video":
            ydl_opts = {
                'format': f'best[filesize<{max_size}M][ext=mp4]/best[filesize<{max_size}M]/best',
                'outtmpl': f'downloads/{user_id}_%(title)s.%(ext)s',
                'quiet': True,
            }
        elif fmt == "photo":
            ydl_opts = {
                'format': 'best',
                'outtmpl': f'downloads/{user_id}_%(title)s.%(ext)s',
                'quiet': True,
            }
        else:  # best
            ydl_opts = {
                'format': f'best[filesize<{max_size}M]/best',
                'outtmpl': f'downloads/{user_id}_%(title)s.%(ext)s',
                'quiet': True,
            }

        await msg.edit_text("📥 Downloading...")

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filepath = ydl.prepare_filename(info)

            # For audio, the extension changes after post-processing
            if fmt == "audio":
                base = os.path.splitext(filepath)[0]
                filepath = base + ".mp3"

            title = info.get("title", "file")
            duration = info.get("duration", 0)

        if not os.path.exists(filepath):
            # Try to find the file
            folder = "downloads"
            files = [f for f in os.listdir(folder) if f.startswith(str(user_id))]
            if files:
                filepath = os.path.join(folder, files[-1])
            else:
                raise FileNotFoundError("Downloaded file not found")

        file_size = os.path.getsize(filepath) / (1024 * 1024)

        # Check file size
        if file_size > max_size:
            os.remove(filepath)
            await msg.edit_text(
                f"❌ File too large ({file_size:.1f} MB).\n"
                f"Free plan limit: 50 MB\n"
                f"Upgrade to Premium for up to 2 GB! 🚀",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🚀 Upgrade", callback_data="upgrade")]
                ])
            )
            return

        await msg.edit_text(f"📤 Uploading... ({file_size:.1f} MB)")

        ext = filepath.split('.')[-1].lower()
        caption = f"✅ **{title}**\n📦 {file_size:.1f} MB | ⏱ {int(duration//60)}:{int(duration%60):02d}" if duration else f"✅ **{title}**\n📦 {file_size:.1f} MB"

        with open(filepath, 'rb') as f:
            if ext in ['mp4', 'mkv', 'webm', 'mov', 'avi']:
                await update.effective_message.reply_video(f, caption=caption, parse_mode="Markdown")
                db.increment_stat(user_id, "video")
            elif ext in ['mp3', 'wav', 'm4a', 'opus', 'flac']:
                await update.effective_message.reply_audio(f, caption=caption, parse_mode="Markdown", title=title)
                db.increment_stat(user_id, "audio")
            elif ext in ['jpg', 'jpeg', 'png', 'webp', 'gif']:
                await update.effective_message.reply_photo(f, caption=caption, parse_mode="Markdown")
                db.increment_stat(user_id, "photo")
            else:
                await update.effective_message.reply_document(f, caption=caption, parse_mode="Markdown")

        os.remove(filepath)
        await msg.delete()

        db.increment_stat(user_id, "total")
        db.increment_stat(user_id, "today")
        db.add_data_mb(user_id, file_size)
        plan_mgr.record_download(user_id)
        log.info(f"Download complete: user={user_id} url={url} size={file_size:.1f}MB")

    except Exception as e:
        log.error(f"Download error: {e}")
        err = str(e)
        if "Private video" in err or "Sign in" in err:
            msg_text = "❌ This video is private or requires login."
        elif "not available" in err.lower():
            msg_text = "❌ This content is not available in your region."
        elif "Unsupported URL" in err:
            msg_text = "❌ This site is not supported."
        else:
            msg_text = f"❌ Download failed:\n`{err[:200]}`"

        try:
            await msg.edit_text(msg_text, parse_mode="Markdown")
        except Exception:
            await update.effective_message.reply_text(msg_text, parse_mode="Markdown")
        finally:
            # Clean up any partial files
            for f in os.listdir("downloads"):
                if f.startswith(str(user_id)):
                    try:
                        os.remove(f"downloads/{f}")
                    except Exception:
                        pass

# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

async def post_init(app):
    """Start the queue worker after bot init."""
    asyncio.create_task(dl_queue.worker(process_download))

def main():
    app = (
        ApplicationBuilder()
        .token(BOT_TOKEN)
        .post_init(post_init)
        .build()
    )

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("plan", cmd_plan))
    app.add_handler(CommandHandler("upgrade", lambda u, c: cmd_plan(u, c)))
    app.add_handler(CommandHandler("stats", cmd_stats))
    app.add_handler(CommandHandler("queue", cmd_queue))
    app.add_handler(CommandHandler("cancel", cmd_cancel))
    app.add_handler(CommandHandler("admin", cmd_admin))
    app.add_handler(CommandHandler("grant", cmd_grant))
    app.add_handler(CommandHandler("revoke", cmd_revoke))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_link))

    log.info("🤖 Bot started!")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
