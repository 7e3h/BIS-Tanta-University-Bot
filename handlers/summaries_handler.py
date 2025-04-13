import os
import logging
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ContextTypes
from utils.logger import log_request

# تفعيل تسجيل الـ Logging
logging.basicConfig(level=logging.INFO)

# المسار الأساسي للملخصات
SUMMARIES_PATH = os.path.join(os.getcwd(), 'summaries')

async def handle_summaries(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the summaries request."""
    user = update.effective_user
    log_request(user.id, user.username, "Summaries Request")

    # إنشاء زر فرقة أولى فقط
    keyboard = [
        [InlineKeyboardButton("فرقة أولى", callback_data="summaries/first_year")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # إضافة زر الرجوع في شريط الكتابة
    reply_keyboard = [[KeyboardButton("🔙 رجوع")]]
    reply_markup_keyboard = ReplyKeyboardMarkup(reply_keyboard, resize_keyboard=True)
    
    await update.message.reply_text(
        "📚 اختر الفرقة الدراسية لعرض الملخصات المتاحة:",
        reply_markup=reply_markup
    )
    await update.message.reply_text(
        "يمكنك الرجوع للقائمة الرئيسية في أي وقت:",
        reply_markup=reply_markup_keyboard
    )

async def handle_summaries_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle callbacks from the summaries menu."""
    query = update.callback_query
    await query.answer()

    path = query.data
    log_request(query.from_user.id, query.from_user.username, f"Summaries Callback: {path}")

    # لو الزر من المجلدات
    if path.startswith("summaries/"):
        relative_path = path.replace("summaries/", "")
        full_path = os.path.join(SUMMARIES_PATH, relative_path)
        
        # التحقق من وجود المسار
        if not os.path.exists(full_path):
            await query.message.edit_text(
                text="❌ عذراً، هذا المسار غير موجود"
            )
            return

        items = os.listdir(full_path)
        keyboard = []

        # إضافة المجلدات أولاً
        for item in sorted(items):
            item_path = os.path.join(full_path, item)
            if os.path.isdir(item_path):
                callback_data = f"summaries/{os.path.join(relative_path, item)}"
                keyboard.append([InlineKeyboardButton(f"📁 {item}", callback_data=callback_data)])

        # إضافة الملفات ثانياً
        for item in sorted(items):
            item_path = os.path.join(full_path, item)
            if os.path.isfile(item_path):
                callback_data = f"download/{os.path.join(relative_path, item)}"
                keyboard.append([InlineKeyboardButton(f"📄 {item}", callback_data=callback_data)])

        if not items:
            keyboard.append([InlineKeyboardButton("❌ لا يوجد ملخصات متاحة حالياً", callback_data="none")])

        reply_markup = InlineKeyboardMarkup(keyboard)
        current_path = relative_path.replace("_", " ").title()
        message_text = f"📚 محتويات {current_path}:" + ("\n\n❌ لا يوجد ملخصات متاحة حالياً" if not items else "")

        # إضافة زر الرجوع في شريط الكتابة
        reply_keyboard = [[KeyboardButton("🔙 رجوع")]]
        reply_markup_keyboard = ReplyKeyboardMarkup(reply_keyboard, resize_keyboard=True)

        await query.message.edit_text(
            text=message_text,
            reply_markup=reply_markup
        )

async def handle_download_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle file download callbacks."""
    query = update.callback_query
    await query.answer()
    
    file_path = query.data.replace("download/", "")
    full_path = os.path.join(SUMMARIES_PATH, file_path)
    
    if not os.path.exists(full_path):
        await query.message.edit_text(
            text="❌ عذراً، الملف غير موجود"
        )
        return
    
    try:
        with open(full_path, 'rb') as file:
            # إضافة زر الرجوع في شريط الكتابة
            reply_keyboard = [[KeyboardButton("🔙 رجوع")]]
            reply_markup_keyboard = ReplyKeyboardMarkup(reply_keyboard, resize_keyboard=True)
            
            await query.message.reply_document(
                document=file,
                filename=os.path.basename(file_path),
                caption=f"📄 {os.path.basename(file_path)}"
            )
    except Exception as e:
        await query.message.edit_text(
            text=f"❌ حدث خطأ أثناء إرسال الملف: {str(e)}"
        )
