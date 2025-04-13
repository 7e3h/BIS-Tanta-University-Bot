import os
import logging
from dotenv import load_dotenv
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler, CallbackQueryHandler
import requests
from bs4 import BeautifulSoup
import json
import urllib3
import ssl
from handlers.login_handler import handle_ssn, handle_password, handle_login
from handlers.logout_handler import handle_logout
from handlers.results_handler import handle_results
from handlers.schedule_handler import handle_schedule
from handlers.attendance_handler import handle_attendance
from utils.shared_data import user_sessions
from utils.logger import log_request, log_website_request

# Import handlers
from handlers.books_handler import handle_books, handle_book_callback
from handlers.summaries_handler import handle_summaries, handle_summaries_callback, handle_download_callback
from handlers.email_handler import handle_email, handle_captcha, cancel_email, CAPTCHA

# Disable SSL verification warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# States for conversation
SSN, PASSWORD = range(2)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start the conversation and ask for SSN."""
    user = update.effective_user
    log_request(user.id, user.username, "/start")
    
    # Check if user is already logged in
    if user.id in user_sessions:
        keyboard = [
            ["📚 الكتب الدراسية"],
            ["📝 ملخصات"],
            ["📧 الايميل الجامعي"],
            ["📊 نتائج الامتحانات"],
            ["🚪 تسجيل الخروج"]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await update.message.reply_text(
            "مرحباً بك في بوت نظم المعلومات الإدارية! 🎓\n"
            "اختر أحد الخيارات التالية:",
            reply_markup=reply_markup
        )
        return ConversationHandler.END
    
    await update.message.reply_text(
        "مرحباً بك في بوت نظم المعلومات الإدارية! 🎓\n"
        "الرجاء إدخال الرقم القومي الخاص بك:"
    )
    return SSN

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel the conversation."""
    user = update.effective_user
    log_request(user.id, user.username, "/cancel")
    
    await update.message.reply_text(
        "تم إلغاء العملية.\n"
        "يمكنك الضغط على /start للبدء مرة أخرى"
    )
    return ConversationHandler.END

async def ssn_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle the SSN input and ask for password."""
    ssn = update.message.text.strip()
    
    # Basic validation for SSN
    if not ssn.isdigit() or len(ssn) != 14:
        await update.message.reply_text(
            "❌ عذراً، الرقم القومي يجب أن يتكون من 14 رقم\n"
            "🔑 الرجاء إدخال الرقم القومي مرة أخرى:"
        )
        return SSN
    
    context.user_data['ssn'] = ssn
    await update.message.reply_text("🔒 الرجاء إدخال كلمة المرور:")
    return PASSWORD

async def password_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle the password input and verify credentials."""
    ssn = context.user_data['ssn']
    password = update.message.text.strip()
    
    # Show waiting message
    wait_message = await update.message.reply_text("⏳ جاري التحقق من البيانات...")
    
    # Verify credentials with Tanta University API
    success, message = await verify_credentials(ssn, password)
    
    # Delete waiting message
    await wait_message.delete()
    
    if success:
        user_sessions[update.effective_user.id] = {
            'ssn': ssn,
            'password': password
        }
        await update.message.reply_text("✅ تم تسجيل الدخول بنجاح! 🎉")
        return await show_main_menu(update, context)
    else:
        await update.message.reply_text(f"❌ {message}")
        return await start(update, context)

async def verify_credentials(ssn: str, password: str) -> tuple[bool, str]:
    """Verify student credentials with Tanta University API."""
    try:
        # Get the login page first to get the form data
        session = requests.Session()
        # Disable SSL verification
        session.verify = False
        login_page = session.get(os.getenv('LOGIN_URL'))
        soup = BeautifulSoup(login_page.text, 'html.parser')
        
        # Extract form data
        viewstate = soup.find('input', {'name': '__VIEWSTATE'})['value']
        viewstategenerator = soup.find('input', {'name': '__VIEWSTATEGENERATOR'})['value']
        eventvalidation = soup.find('input', {'name': '__EVENTVALIDATION'})['value']
        
        # Prepare login data
        login_data = {
            '__EVENTTARGET': '',
            '__EVENTARGUMENT': '',
            '__VIEWSTATE': viewstate,
            '__VIEWSTATEGENERATOR': viewstategenerator,
            '__EVENTVALIDATION': eventvalidation,
            'DDLFaculty': '8',
            'txtStudSSN': ssn,
            'txtStudPW': password,
            'loginButton': 'دخول'
        }
        
        # Perform login
        response = session.post(os.getenv('LOGIN_URL'), data=login_data)
        
        if '/ebooks/StudHome.aspx' in response.url:
            # Check if student is from BIS department
            home_page = session.get(os.getenv('HOME_URL'))
            soup = BeautifulSoup(home_page.text, 'html.parser')
            department = soup.find('span', {'id': 'lbl_department'})
            
            if department and 'نظم معلومات الأعمال' in department.text:
                return True, "تم تسجيل الدخول بنجاح"
            else:
                return False, "عذراً، هذا البوت مخصص فقط لطلاب نظم معلومات الأعمال (BIS)"
        else:
            return False, "خطأ في الرقم القومي أو كلمة المرور"
            
    except Exception as e:
        logger.error(f"Error during verification: {str(e)}")
        return False, "حدث خطأ أثناء التحقق من البيانات، الرجاء المحاولة مرة أخرى"

async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Show the main menu with all options."""
    keyboard = [
        ["📚 الكتب الدراسية"],
        ["📝 ملخصات"],
        ["📧 الايميل الجامعي"],
        ["📊 نتائج الامتحانات"],
        ["🚪 تسجيل الخروج"]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text(
        "🏠 القائمة الرئيسية\n"
        "اختر أحد الخيارات التالية:",
        reply_markup=reply_markup
    )
    return ConversationHandler.END

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle incoming messages."""
    user = update.effective_user
    message = update.message.text
    
    # Log the message
    log_request(user.id, user.username, f"Message: {message}")
    
    # Check if user is authenticated
    if user.id not in user_sessions and message != "/start":
        await update.message.reply_text(
            "❌ عذراً، يجب عليك تسجيل الدخول أولاً\n"
            "اضغط /start للبدء"
        )
        log_request(user.id, user.username, "Message - Not Authenticated", "FAILED")
        return
    
    # Handle back button
    if message == "🔙 رجوع":
        # Create main menu keyboard
        keyboard = [
            ["📚 الكتب الدراسية"],
            ["📝 ملخصات"],
            ["📧 الايميل الجامعي"],
            ["📊 نتائج الامتحانات"],
            ["🚪 تسجيل الخروج"]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        await update.message.reply_text(
            "🔙 تم العودة للقائمة الرئيسية\n"
            "اختر أحد الخيارات التالية:",
            reply_markup=reply_markup
        )
        log_request(user.id, user.username, "Back to Main Menu", "SUCCESS")
        return
    
    # Handle main menu buttons
    if message == "📚 الكتب الدراسية":
        await handle_books(update, context)
    elif message == "📝 ملخصات":
        await handle_summaries(update, context)
    elif message == "📧 الايميل الجامعي":
        await handle_email(update, context)
    elif message == "📊 نتائج الامتحانات":
        await handle_results(update, context)
    elif message == "🚪 تسجيل الخروج":
        await handle_logout(update, context)
    else:
        # Create main menu keyboard
        keyboard = [
            ["📚 الكتب الدراسية"],
            ["📝 ملخصات"],
            ["📧 الايميل الجامعي"],
            ["📊 نتائج الامتحانات"],
            ["🚪 تسجيل الخروج"]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        await update.message.reply_text(
            "❓ لم أفهم طلبك\n"
            "اختر أحد الخيارات التالية:",
            reply_markup=reply_markup
        )
        log_request(user.id, user.username, "Unknown Message", "FAILED")

def main() -> None:
    """Start the bot."""
    # Log bot startup
    log_website_request(
        url="BOT_STARTUP",
        method="START",
        data={
            "bot_token": os.getenv('BOT_TOKEN')[:10] + "..." if os.getenv('BOT_TOKEN') else None,
            "login_url": os.getenv('LOGIN_URL'),
            "results_url": os.getenv('RESULTS_URL'),
            "base_url": os.getenv('BASE_URL')
        }
    )
    
    # Create the Application and pass it your bot's token
    application = Application.builder().token(os.getenv('BOT_TOKEN')).build()

    # Add conversation handler for login
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            SSN: [MessageHandler(filters.TEXT & ~filters.COMMAND, ssn_handler)],
            PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, password_handler)]
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )

    # Add email conversation handler
    email_conv_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex('^📧 الايميل الجامعي$'), handle_email)],
        states={
            CAPTCHA: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_captcha)]
        },
        fallbacks=[CommandHandler('cancel', cancel_email)]
    )

    # Add handlers
    application.add_handler(conv_handler)
    application.add_handler(email_conv_handler)
    application.add_handler(MessageHandler(filters.Regex('^📊 نتائج الامتحانات$'), handle_results))
    application.add_handler(MessageHandler(filters.Regex('^📅 الجدول الدراسي$'), handle_schedule))
    application.add_handler(MessageHandler(filters.Regex('^✅ الحضور والغياب$'), handle_attendance))
    application.add_handler(MessageHandler(filters.Regex('^🚪 تسجيل الخروج$'), handle_logout))
    application.add_handler(MessageHandler(filters.TEXT, handle_message))

    # Add callback query handlers for summaries
    application.add_handler(CallbackQueryHandler(handle_summaries_callback, pattern="^summaries/"))
    application.add_handler(CallbackQueryHandler(handle_download_callback, pattern="^download/"))

    # Add callback query handlers for books
    application.add_handler(CallbackQueryHandler(handle_book_callback, pattern="^book_"))
    application.add_handler(CallbackQueryHandler(handle_download_callback, pattern="^download_"))

    # Start the Bot
    application.run_polling()

if __name__ == '__main__':
    main() 