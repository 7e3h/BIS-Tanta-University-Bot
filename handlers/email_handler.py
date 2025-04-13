from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ContextTypes, ConversationHandler
import requests
from bs4 import BeautifulSoup
import urllib3
import ssl
import os
import re
from dotenv import load_dotenv
import io

# Import shared data and logger
from utils.shared_data import user_sessions
from utils.logger import log_request, log_website_request

# Load environment variables
load_dotenv()

# Disable SSL verification warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Define conversation states
CAPTCHA = 1

async def handle_email(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle the university email request."""
    user = update.effective_user
    log_request(user.id, user.username, "Email Request")
    
    # Check if user is authenticated
    if user.id not in user_sessions:
        await update.message.reply_text(
            "❌ عذراً، يجب عليك تسجيل الدخول أولاً\n"
            "اضغط /start للبدء"
        )
        log_request(user.id, user.username, "Email Request - Not Authenticated", "FAILED")
        return ConversationHandler.END
    
    # Create back button
    keyboard = [[KeyboardButton("🔙 رجوع")]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    # Show waiting message
    wait_message = await update.message.reply_text(
        "⏳ جاري جلب معلومات البريد الإلكتروني...",
        reply_markup=reply_markup
    )
    
    try:
        # Get user credentials
        user_data = user_sessions[user.id]
        ssn = user_data['ssn']
        
        # Create a session
        session = requests.Session()
        session.verify = False
        
        # Define URLs
        captcha_url = "https://tdb.tanta.edu.eg/newemailservices/Captcha.aspx"
        email_url = "https://tdb.tanta.edu.eg/newemailservices/pw_reset.aspx"
        
        # Get the captcha image
        captcha_response = session.get(captcha_url)
        
        # Extract ASP.NET_SessionId cookie
        session_id = None
        for cookie in session.cookies:
            if cookie.name == 'ASP.NET_SessionId':
                session_id = cookie.value
                break
        
        if not session_id:
            await wait_message.delete()
            await update.message.reply_text(
                "❌ حدث خطأ أثناء جلب معلومات البريد الإلكتروني، حاول لاحقاً",
                reply_markup=reply_markup
            )
            log_request(user.id, user.username, "Email Request - No Session ID", "FAILED")
            return ConversationHandler.END
        
        # Log the captcha request
        log_website_request(
            url=captcha_url,
            method="GET",
            response={"status_code": captcha_response.status_code, "session_id": session_id}
        )
        
        # Store the captcha image in the context for later use
        context.user_data['captcha_image'] = captcha_response.content
        
        # Store the session in the context for later use
        context.user_data['session'] = session
        
        # Store the SSN in the context for later use
        context.user_data['ssn'] = ssn
        
        # Store the email URL in the context for later use
        context.user_data['email_url'] = email_url
        
        # Store the session ID in the context for later use
        context.user_data['session_id'] = session_id
        
        # Delete waiting message
        await wait_message.delete()
        
        # Send the captcha image to the user
        await update.message.reply_photo(
            photo=io.BytesIO(captcha_response.content),
            caption="🔍 الرجاء إدخال الكابتشا المظاهرة في الصورة:",
            reply_markup=reply_markup
        )
        
        log_request(user.id, user.username, "Email Request - Captcha Sent", "SUCCESS")
        
        return CAPTCHA
        
    except Exception as e:
        # Delete waiting message
        await wait_message.delete()
        await update.message.reply_text(
            "❌ حدث خطأ أثناء جلب معلومات البريد الإلكتروني، حاول لاحقاً",
            reply_markup=reply_markup
        )
        log_request(user.id, user.username, f"Email Request - Error: {str(e)}", "FAILED")
        return ConversationHandler.END

async def handle_captcha(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle the captcha input."""
    user = update.effective_user
    text = update.message.text.strip()
    
    # Check if user pressed the back button
    if text == "🔙 رجوع":
        return await cancel_email(update, context)
    
    captcha = text
    
    log_request(user.id, user.username, "Captcha Input", data={"captcha": captcha})
    
    # Create back button
    keyboard = [[KeyboardButton("🔙 رجوع")]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    # Show waiting message
    wait_message = await update.message.reply_text(
        "⏳ جاري التحقق من الكابتشا...",
        reply_markup=reply_markup
    )
    
    try:
        # Get the stored data from the context
        session = context.user_data.get('session')
        ssn = context.user_data.get('ssn')
        email_url = context.user_data.get('email_url')
        session_id = context.user_data.get('session_id')
        
        if not all([session, ssn, email_url, session_id]):
            await wait_message.delete()
            await update.message.reply_text(
                "❌ حدث خطأ أثناء التحقق من الكابتشا، حاول مرة أخرى",
                reply_markup=reply_markup
            )
            log_request(user.id, user.username, "Captcha Input - Missing Context Data", "FAILED")
            return ConversationHandler.END
        
        # Set the ASP.NET_SessionId cookie for the request
        #session.cookies.set('ASP.NET_SessionId', session_id)
        
        # Get the email page to extract form data
        email_page = session.get(email_url)
        soup = BeautifulSoup(email_page.text, 'html.parser')
        
        # Extract form data
        viewstate = soup.find('input', {'name': '__VIEWSTATE'})['value']
        viewstategenerator = soup.find('input', {'name': '__VIEWSTATEGENERATOR'})['value']
        eventvalidation = soup.find('input', {'name': '__EVENTVALIDATION'})['value']
        
        # Prepare the payload for the email request
        email_data = {
            '__EVENTTARGET': '',
            '__EVENTARGUMENT': '',
            '__VIEWSTATE': viewstate,
            '__VIEWSTATEGENERATOR': viewstategenerator,
            '__EVENTVALIDATION': eventvalidation,
            'DropDownList1': '8',
            'txtCaptcha': captcha,
            'TextBox1': ssn,
            'Button1': 'عرض البيانات'
        }
        

        # Log the email request
        log_website_request(
            url=email_url,
            method="POST",
            data={**email_data},
            response={"url": email_page.url, "session_id": session_id}
        )
        
        # Send the email request
        email_response = session.post(email_url, data=email_data)
        
        # Log the email response
        log_website_request(
            url=email_url,
            method="POST",
            data={**email_data},
            response={"url": email_response.url, "status_code": email_response.status_code, "session_id": session_id}
        )
        
        # Parse the response
        soup = BeautifulSoup(email_response.text, 'html.parser')
        
        # Find the email span
        email_span = soup.find('span', {'id': 'lbl_email_tag'})
        if not email_span:
            await wait_message.delete()
            await update.message.reply_text(
                "❌ لم يتم العثور على البريد الإلكتروني، تأكد من صحة الكابتشا وحاول مرة أخرى",
                reply_markup=reply_markup
            )
            log_request(user.id, user.username, "Captcha Input - Email Not Found", "FAILED")
            return ConversationHandler.END
        
        email = email_span.text.strip()
        
        # Get the form data for the password reset request
        viewstate = soup.find('input', {'name': '__VIEWSTATE'})['value']
        viewstategenerator = soup.find('input', {'name': '__VIEWSTATEGENERATOR'})['value']
        eventvalidation = soup.find('input', {'name': '__EVENTVALIDATION'})['value']
        

        # Prepare the payload for the password reset request
        password_data = {
            'ScriptManager1': 'UpdatePanel1|Button2',
            '__EVENTTARGET': '',
            '__EVENTARGUMENT': '',
            '__VIEWSTATE': viewstate,
            '__VIEWSTATEGENERATOR': viewstategenerator,
            '__EVENTVALIDATION': eventvalidation,
            'DropDownList1': '8',
            'txtCaptcha': captcha,
            'TextBox1': ssn,
            '__ASYNCPOST': 'true',
            'Button2': 'إعادة ضبط كلمة المرور'
        }
        
        headers = {
    "Accept": "*/*",
    "Accept-Encoding": "gzip, deflate, br, zstd",
    "Accept-Language": "en-US,en;q=0.8",
    "Cache-Control": "no-cache",
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    "Origin": "https://tdb.tanta.edu.eg",
    "Priority": "u=1, i",
    "Referer": "https://tdb.tanta.edu.eg/newemailservices/pw_reset.aspx",
    "Sec-Ch-Ua": '"Brave";v="135", "Not-A.Brand";v="8", "Chromium";v="135"',
    "Sec-Ch-Ua-Mobile": "?0",
    "Sec-Ch-Ua-Platform": '"Windows"',
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-origin",
    "Sec-GPC": "1",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36",
    "X-MicrosoftAjax": "Delta=true",
    "X-Requested-With": "XMLHttpRequest",
    "Cookie": f"ASP.NET_SessionId={session_id}"
}
        # Log the password reset request
        log_website_request(
            url=email_url,
            method="POST",
            data={**password_data},
            response={"url": email_response.url, "session_id": session_id}
        )
        
        # Send the password reset request
        password_response = session.post(email_url, data=password_data, headers=headers)
        
        # Log the password reset response
        log_website_request(
            url=email_url,
            method="POST",
            data={**password_data},
            response={"url": password_response.url, "status_code": password_response.status_code, "session_id": session_id}
        )
        
        # Parse the response
        soup = BeautifulSoup(password_response.text, 'html.parser')
        
        # Find the password span
        password_span = soup.find('span', {'id': 'lbl_newPW'})
        if not password_span:
            await wait_message.delete()
            await update.message.reply_text(
                f"📧 البريد الإلكتروني الخاص بك هو: {email}\n\n"
                "❌ لم يتم العثور على كلمة المرور، حاول مرة أخرى لاحقاً",
                reply_markup=reply_markup
            )
            log_request(user.id, user.username, "Captcha Input - Password Not Found", "FAILED")
            return ConversationHandler.END
        
        password = password_span.text.strip()
        
        # Delete waiting message
        await wait_message.delete()
        
        # Create main menu keyboard
        keyboard = [
            ["📚 الكتب الدراسية"],
            ["📝 ملخصات"],
            ["📧 الايميل الجامعي"],
            ["📊 نتائج الامتحانات"],
            ["🚪 تسجيل الخروج"]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        # Send the email and password to the user
        await update.message.reply_text(
            f"📧 البريد الإلكتروني الخاص بك هو: {email}\n"
            f"🔑 كلمة المرور الخاصة بك هي: {password}\n\n"
            "🔙 للعودة للقائمة الرئيسية، اختر أحد الخيارات التالية:",
            reply_markup=reply_markup
        )
        
        log_request(user.id, user.username, "Captcha Input - Success", "SUCCESS", data={"email": email, "password": password})
        
        return ConversationHandler.END
        
    except Exception as e:
        # Delete waiting message
        await wait_message.delete()
        await update.message.reply_text(
            "❌ حدث خطأ أثناء التحقق من الكابتشا، حاول لاحقاً",
            reply_markup=reply_markup
        )
        log_request(user.id, user.username, f"Captcha Input - Error: {str(e)}", "FAILED")
        return ConversationHandler.END

async def cancel_email(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel the email request."""
    user = update.effective_user
    log_request(user.id, user.username, "Email Request - Cancelled")
    
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
        "❌ تم إلغاء طلب البريد الإلكتروني\n\n"
        "🔙 للعودة للقائمة الرئيسية، اختر أحد الخيارات التالية:",
        reply_markup=reply_markup
    )
    
    return ConversationHandler.END 