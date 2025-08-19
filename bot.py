import os
import json
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "0"))
DB_FILE = "media_db.json"

# بارگذاری دیتابیس
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

def is_admin(user_id: int) -> bool:
    return ADMIN_ID != 0 and user_id == ADMIN_ID

# ذخیره فایل
async def save_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await update.message.reply_text("⛔ شما ادمین نیستید.")
        return
    
    if not context.args:
        await update.message.reply_text("باید شماره فایل بدی. مثال: /save 1 همراه فایل")
        return

    media_id = context.args[0]
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
        await update.message.reply_text("❌ باید همراه دستور، ویدیو/گیف/عکس بفرستی.")
        return

    media_db[media_id] = {"file_id": file_id, "type": file_type}
    save_db()

    await update.message.reply_text(f"✅ فایل با شماره {media_id} ذخیره شد.")

# گرفتن فایل
async def get_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("مثال: /get 1")
        return

    media_id = context.args[0]
    info = media_db.get(media_id)
    if not info:
        await update.message.reply_text("⛔ این شماره ذخیره نشده.")
        return

    if info["type"] == "animation":
        await update.message.reply_animation(animation=info["file_id"])
    elif info["type"] == "video":
        await update.message.reply_video(video=info["file_id"])
    elif info["type"] == "photo":
        await update.message.reply_photo(photo=info["file_id"])
    else:
        await update.message.reply_text("نوع فایل ناشناخته است.")

def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("save", save_media))
    app.add_handler(CommandHandler("get", get_media))

    app.run_polling()

if __name__ == "__main__":
    main()
