import os
import json
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "0"))
DB_FILE = "media_db.json"

if os.path.exists(DB_FILE):
    with open(DB_FILE, "r", encoding="utf-8") as f:
        try:
            media_db = json.load(f)
        except json.JSONDecodeError:
            media_db = {}
else:
    media_db = {}

def save_db():
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(media_db, f, ensure_ascii=False, indent=2)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("سلام ✌️ برای ذخیره تستی، یک ویدیو/گیف با کپشن `/save 1` بفرست.")

async def save_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        await update.message.reply_text("⛔ فقط ادمین می‌تونه ذخیره کنه.")
        return
    
    if not context.args:
        await update.message.reply_text("❌ شماره فایل رو بده. مثال: `/save 3`")
        return

    media_id = context.args[0].strip()
    file_id, file_type = None, None

    if update.message.animation:
        file_id = update.message.animation.file_id
        file_type = "animation"
    elif update.message.video:
        file_id = update.message.video.file_id
        file_type = "video"
    elif update.message.photo:
        file_id = update.message.photo[-1].file_id
        file_type = "photo"

    if not file_id:
        await update.message.reply_text("❌ باید همراه دستور، ویدیو/گیف/عکس ارسال کنی.")
        return

    media_db[media_id] = {"file_id": file_id, "type": file_type}
    save_db()
    await update.message.reply_text(f"✅ فایل با شماره {media_id} ذخیره شد. نوع: {file_type}")

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("save", save_media))
    app.run_polling()

if __name__ == "__main__":
    main()
