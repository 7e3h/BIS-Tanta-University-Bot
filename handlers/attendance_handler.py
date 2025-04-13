from telegram import Update
from telegram.ext import ContextTypes
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

async def handle_attendance(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the attendance request."""
    user = update.effective_user
    log_request(user.id, user.username, "Attendance Request")
    
    # Check if user is authenticated
    if user.id not in user_sessions:
        await update.message.reply_text(
            "❌ عذراً، يجب عليك تسجيل الدخول أولاً\n"
            "اضغط /start للبدء"
        )
        log_request(user.id, user.username, "Attendance Request - Not Authenticated", "FAILED")
        return
    
    # Show waiting message
    wait_message = await update.message.reply_text("⏳ جاري جلب بيانات الحضور والغياب...")
    
    try:
        # Get user credentials
        user_data = user_sessions[user.id]
        ssn = user_data['ssn']
        password = user_data['password']
        
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
            await update.message.reply_text("❌ فشل تسجيل الدخول، الرجاء المحاولة مرة أخرى")
            log_request(user.id, user.username, "Attendance Request - Login Failed", "FAILED")
            return
        
        # Navigate to attendance page
        attendance_url = os.getenv('ATTENDANCE_URL')
        attendance_page = session.get(attendance_url)
        
        # Log the attendance page request
        log_website_request(
            url=attendance_url,
            method="GET",
            response={"url": attendance_page.url, "status_code": attendance_page.status_code}
        )
        
        soup = BeautifulSoup(attendance_page.text, 'html.parser')
        
        # Find the attendance table
        attendance_table = soup.find('table', {'id': 'attendanceTable'})
        if not attendance_table:
            await wait_message.delete()
            await update.message.reply_text("❌ لم يتم العثور على بيانات الحضور والغياب")
            log_request(user.id, user.username, "Attendance Request - Table Not Found", "FAILED")
            return
        
        # Extract attendance data
        attendance_data = []
        rows = attendance_table.find_all('tr')[1:]  # Skip header row
        
        for row in rows:
            cols = row.find_all('td')
            if len(cols) >= 4:
                course = cols[0].text.strip()
                total_classes = cols[1].text.strip()
                attended_classes = cols[2].text.strip()
                percentage = cols[3].text.strip()
                
                attendance_data.append({
                    'course': course,
                    'total_classes': total_classes,
                    'attended_classes': attended_classes,
                    'percentage': percentage
                })
        
        # Delete waiting message
        await wait_message.delete()
        
        # Format attendance message
        attendance_message = "✅ بيانات الحضور والغياب:\n\n"
        
        for item in attendance_data:
            attendance_message += f"📚 {item['course']}\n"
            attendance_message += f"📊 الحضور: {item['attended_classes']}/{item['total_classes']} ({item['percentage']})\n\n"
        
        # Send the attendance data
        await update.message.reply_text(
            f"{attendance_message}\n"
            "🔙 للعودة للقائمة الرئيسية، اختر أحد الخيارات التالية:"
        )
        log_request(user.id, user.username, "Attendance Request - Success", "SUCCESS", data={"attendance": attendance_data})
        
    except Exception as e:
        # Delete waiting message
        await wait_message.delete()
        await update.message.reply_text(
            "❌ حدث خطأ أثناء جلب بيانات الحضور والغياب\n"
            "الرجاء المحاولة مرة أخرى لاحقاً"
        )
        log_request(user.id, user.username, f"Attendance Request - Error: {str(e)}", "FAILED") 