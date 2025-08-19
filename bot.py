import os
import json
from typing import Dict, Any, Tuple, Optional

from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup, Message, ChatMember
)
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ContextTypes, filters
)

# ========= تنظیمات و متغیرهای محیطی =========
BOT_TOKEN = os.environ.get("BOT_TOKEN", "").strip()
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is required as an environment variable.")

ADMIN_ID = int(os.environ.get("ADMIN_ID", "0"))  # عددی
DB_FILE = os.environ.get("DB_FILE", "media_db.json")

# کانال‌ها را می‌توان از ENV به صورت JSON داد: e.g. ["@ch1","@ch2"]
CHANNELS_ENV = os.environ.get("CHANNELS_JSON", "").strip()
if CHANNELS_ENV:
    try:
        CHANNELS = json.loads(CHANNELS_ENV)
        if not isinstance(CHANNELS, list):
            raise ValueError
    except Exception:
        raise RuntimeError("CHANNELS_JSON must be a JSON array of channel usernames, e.g. [\"@ch1\",\"@ch2\"]")
else:
    # fallback: اگر ENV ندادید این‌ها استفاده می‌شود
    CHANNELS = ["@example_channel_1", "@example_channel_2"]

# ========= لود دیتابیس ساده فایل JSON =========
if os.path.exists(DB_FILE):
    try:
        with open(DB_FILE, "r", encoding="utf-8") as f:
            media_db: Dict[str, Dict[str, str]] = json.load(f)
    except Exception:
        media_db = {}
else:
    media_db = {}

def save_db() -> None:
    tmp = DB_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(media_db, f, ensure_ascii=False, indent=2)
    os.replace(tmp, DB_FILE)

# درخواست در انتظار بررسی عضویت: user_id -> media_id
pending_requests: Dict[int, str] = {}


# ========= کمک‌تابع‌ها =========
def is_admin(user_id: int) -> bool:
    return ADMIN_ID != 0 and user_id == ADMIN_ID

def extract_media_from_message(msg: Message) -> Tuple[Optional[str], Optional[str]]:
    """
    برمی‌گرداند (file_id, media_type)
    انواع پشتیبانی: animation (گیف)، video، photo، document
    """
    if msg.animation:
        return msg.animation.file_id, "animation"
    if msg.video:
        return msg.video.file_id, "video"
    if msg.photo:
        # آخرین سایز بهترین کیفیت
        return msg.photo[-1].file_id, "photo"
    if msg.document:
        return msg.document.file_id, "document"
    return None, None


# ========= دستورات =========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "سلام! 👋\n"
        "برای دریافت فایل:\n"
        "• شماره فایل را بزن: /get 12\n\n"
        "برای ذخیره (فقط ادمین):\n"
        "• همراه فایل بنویس: /save 12\n\n"
        "سایر دستورات:\n"
        "• /channels – دیدن کانال‌های تبلیغاتی\n"
        "• /whoami – دیدن آیدی عددی خودت"
    )
    await update.message.reply_text(text)

async def whoami(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"Your numeric user id: {update.effective_user.id}")

async def channels_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not CHANNELS:
        await update.message.reply_text("هیچ کانالی تنظیم نشده.")
        return
    buttons = [[InlineKeyboardButton(ch, url=f"https://t.me/{ch.strip('@')}")] for ch in CHANNELS]
    await update.message.reply_text(
        "برای استفاده باید در همه کانال‌های زیر عضو باشید:",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

async def save_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    روش ۱ (پیشنهادی): ادمین فایل را در همان پیام به همراه /save 123 بفرستد.
    روش ۲: ادمین فایل را با کپشن '#123' بفرستد (هندلر جداگانه پایین).
    """
    user_id = update.effective_user.id
    if not is_admin(user_id):
        return  # سکوت برای بقیه

    if not context.args:
        await update.message.reply_text("مثال: همراه فایل بفرست: /save 7")
        return

    media_id = context.args[0].strip()
    file_id, media_type = extract_media_from_message(update.message)

    if not file_id:
        await update.message.reply_text("❌ باید همراه دستور، عکس/ویدیو/گیف/فایل ارسال کنی.")
        return

    media_db[media_id] = {"file_id": file_id, "type": media_type}
    save_db()
    await update.message.reply_text(f"✅ ذخیره شد: شماره {media_id} | نوع: {media_type}")

async def save_by_caption(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    روش ۲: ادمین فایل را با کپشن مثل '#123' بفرستد.
    """
    user_id = update.effective_user.id
    if not is_admin(user_id):
        return

    msg = update.message
    if not msg.caption:
        return

    cap = msg.caption.strip()
    # کپشن باید مثل #123 باشد
    if not (cap.startswith("#") and len(cap) > 1):
        return

    media_id = cap[1:].strip()
    file_id, media_type = extract_media_from_message(msg)
    if not file_id:
        await msg.reply_text("❌ فایل شناسایی نشد.")
        return

    media_db[media_id] = {"file_id": file_id, "type": media_type}
    save_db()
    await msg.reply_text(f"✅ ذخیره شد: شماره {media_id} | نوع: {media_type}")

async def get_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("لطفاً شماره فایل را وارد کن. مثال: /get 2")
        return
    media_id = context.args[0].strip()
    if media_id not in media_db:
        await update.message.reply_text("⛔ چنین شماره‌ای ذخیره نشده.")
        return

    user_id = update.effective_user.id
    pending_requests[user_id] = media_id

    # دکمه‌های عضویت + دکمه «عضو شدم»
    buttons = [[InlineKeyboardButton(f"عضویت در {ch}", url=f"https://t.me/{ch.strip('@')}")] for ch in CHANNELS]
    buttons.append([InlineKeyboardButton("✅ عضو شدم", callback_data="check_subs")])

    await update.message.reply_text(
        "برای دریافت فایل، اول در همه کانال‌ها عضو شو و بعد روی «عضو شدم» بزن.",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

async def check_subs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    # بررسی عضویت تک‌تک کانال‌ها
    for ch in CHANNELS:
        try:
            member: ChatMember = await context.bot.get_chat_member(ch, user_id)
            if member.status not in ("member", "administrator", "creator"):
                await query.edit_message_text("⛔ باید در همه کانال‌ها عضو باشی. بعد دوباره امتحان کن.")
                return
        except Exception:
            await query.edit_message_text(
                f"❌ خطا در بررسی عضویت در {ch}.\n"
                f"کانال باید پابلیک باشد و من حتماً داخل کانال ادمین/عضو باشم."
            )
            return

    # اگر همه عضو بودند
    media_id = pending_requests.pop(user_id, None)
    if not media_id:
        await query.edit_message_text("درخواستی برای فایل ثبت نشده.")
        return

    info = media_db.get(media_id)
    if not info:
        await query.edit_message_text("⛔ فایل مورد نظر پیدا نشد.")
        return

    await query.edit_message_text("✅ تایید شد! در حال ارسال فایل...")

    mtype = info.get("type")
    fid = info.get("file_id")
    try:
        if mtype == "animation":
            await context.bot.send_animation(chat_id=user_id, animation=fid)
        elif mtype == "video":
            await context.bot.send_video(chat_id=user_id, video=fid)
        elif mtype == "photo":
            await context.bot.send_photo(chat_id=user_id, photo=fid)
        elif mtype == "document":
            await context.bot.send_document(chat_id=user_id, document=fid)
        else:
            await context.bot.send_message(chat_id=user_id, text="Unknown media type.")
    except Exception as e:
        await context.bot.send_message(chat_id=user_id, text=f"❌ خطا در ارسال فایل: {e}")


# ========= اجرای برنامه (Webhook برای Render) =========
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    # Commands
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("whoami", whoami))
    app.add_handler(CommandHandler("channels", channels_cmd))
    app.add_handler(CommandHandler("save", save_cmd))
    app.add_handler(CommandHandler("get", get_media))

    # Callback for "عضو شدم"
    app.add_handler(CallbackQueryHandler(check_subs, pattern="^check_subs$"))

    # Save by caption like "#123" (admin only)
    app.add_handler(MessageHandler(
        filters.Caption() & (filters.PHOTO | filters.VIDEO | filters.ANIMATION | filters.Document.ALL),
        save_by_caption
    ))

    # --- وبهوک برای Render ---
    port = int(os.environ.get("PORT", "10000"))
    external = os.environ.get("RENDER_EXTERNAL_HOSTNAME")
    if not external:
        # اگر لوکال ران می‌کنید یا خارج از Render هستید می‌توانید polling بگذارید:
        # app.run_polling()
        raise RuntimeError("RENDER_EXTERNAL_HOSTNAME not set. Are you running on Render Web Service?")

    webhook_url = f"https://{external}/{BOT_TOKEN}"
    app.run_webhook(
        listen="0.0.0.0",
        port=port,
        url_path=BOT_TOKEN,
        webhook_url=webhook_url,
    )

if __name__ == "__main__":
    main()
