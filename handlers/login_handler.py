from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ContextTypes, ConversationHandler
import requests
from bs4 import BeautifulSoup
import urllib3
import ssl
import os
from dotenv import load_dotenv

# Import shared data and logger
from utils.shared_data import user_sessions
from utils.logger import log_request, log_website_request

# Load environment variables
load_dotenv()

# Disable SSL verification warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

async def handle_ssn(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle the SSN input."""
    user = update.effective_user
    log_request(user.id, user.username, "SSN Input", data={"ssn": update.message.text})
    
    # Store SSN in context
    context.user_data['ssn'] = update.message.text
    
    # Ask for password
    await update.message.reply_text("الرجاء إدخال كلمة المرور:")
    return PASSWORD

async def handle_password(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle the password input."""
    user = update.effective_user
    log_request(user.id, user.username, "Password Input", data={"password": "********"})
    
    # Store password in context
    context.user_data['password'] = update.message.text
    
    # Try to login
    return await handle_login(update, context)

async def handle_login(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle the login process."""
    user = update.effective_user
    log_request(user.id, user.username, "Login Attempt")
    
    # Get credentials from context
    ssn = context.user_data.get('ssn')
    password = context.user_data.get('password')
    
    if not ssn or not password:
        await update.message.reply_text(
            "❌ حدث خطأ في عملية تسجيل الدخول\n"
            "الرجاء المحاولة مرة أخرى باستخدام /start"
        )
        log_request(user.id, user.username, "Login Failed - Missing Credentials", "FAILED")
        return ConversationHandler.END
    
    # Show waiting message
    wait_message = await update.message.reply_text("⏳ جاري تسجيل الدخول...")
    
    try:
        # Create a session
        session = requests.Session()
        session.verify = False
        
        # Get the login page first to get the form data
        login_url = os.getenv('LOGIN_URL')
        login_page = session.get(login_url)
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
        
        # Log the login request
        log_website_request(
            url=login_url,
            method="POST",
            data={**login_data, 'txtStudPW': '********'},  # Hide password in logs
            response={"url": login_page.url}
        )
        
        # Perform login
        response = session.post(login_url, data=login_data)
        
        # Log the login response
        log_website_request(
            url=login_url,
            method="POST",
            data={**login_data, 'txtStudPW': '********'},  # Hide password in logs
            response={"url": response.url, "status_code": response.status_code}
        )
        
        if '/ebooks/StudHome.aspx' not in response.url:
            await wait_message.delete()
            await update.message.reply_text(
                "❌ فشل تسجيل الدخول\n"
                "الرجاء التأكد من صحة البيانات والمحاولة مرة أخرى"
            )
            log_request(user.id, user.username, "Login Failed - Invalid Credentials", "FAILED")
            return ConversationHandler.END
        
        # Store user session
        user_sessions[user.id] = {
            'ssn': ssn,
            'password': password,
            'session': session
        }
        
        # Delete waiting message
        await wait_message.delete()
        
        # Create keyboard
        keyboard = [
            [KeyboardButton("📊 نتائج الامتحانات"), KeyboardButton("📅 الجدول الدراسي")],
            [KeyboardButton("✅ الحضور والغياب"), KeyboardButton("🚪 تسجيل الخروج")]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        # Send success message
        await update.message.reply_text(
            "✅ تم تسجيل الدخول بنجاح!\n\n"
            "اختر أحد الخيارات التالية:",
            reply_markup=reply_markup
        )
        log_request(user.id, user.username, "Login Success", "SUCCESS")
        return ConversationHandler.END
        
    except Exception as e:
        # Delete waiting message
        await wait_message.delete()
        await update.message.reply_text(
            "❌ حدث خطأ أثناء تسجيل الدخول\n"
            "الرجاء المحاولة مرة أخرى لاحقاً"
        )
        log_request(user.id, user.username, f"Login Failed - Error: {str(e)}", "FAILED")
        return ConversationHandler.END 