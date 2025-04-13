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

async def handle_schedule(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the schedule request."""
    user = update.effective_user
    log_request(user.id, user.username, "Schedule Request")
    
    # Check if user is authenticated
    if user.id not in user_sessions:
        await update.message.reply_text(
            "❌ عذراً، يجب عليك تسجيل الدخول أولاً\n"
            "اضغط /start للبدء"
        )
        log_request(user.id, user.username, "Schedule Request - Not Authenticated", "FAILED")
        return
    
    # Show waiting message
    wait_message = await update.message.reply_text("⏳ جاري جلب الجدول الدراسي...")
    
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
            log_request(user.id, user.username, "Schedule Request - Login Failed", "FAILED")
            return
        
        # Navigate to schedule page
        schedule_url = os.getenv('SCHEDULE_URL')
        schedule_page = session.get(schedule_url)
        
        # Log the schedule page request
        log_website_request(
            url=schedule_url,
            method="GET",
            response={"url": schedule_page.url, "status_code": schedule_page.status_code}
        )
        
        soup = BeautifulSoup(schedule_page.text, 'html.parser')
        
        # Find the schedule table
        schedule_table = soup.find('table', {'id': 'scheduleTable'})
        if not schedule_table:
            await wait_message.delete()
            await update.message.reply_text("❌ لم يتم العثور على الجدول الدراسي")
            log_request(user.id, user.username, "Schedule Request - Table Not Found", "FAILED")
            return
        
        # Extract schedule data
        schedule_data = []
        rows = schedule_table.find_all('tr')[1:]  # Skip header row
        
        for row in rows:
            cols = row.find_all('td')
            if len(cols) >= 5:
                day = cols[0].text.strip()
                time = cols[1].text.strip()
                course = cols[2].text.strip()
                room = cols[3].text.strip()
                professor = cols[4].text.strip()
                
                schedule_data.append({
                    'day': day,
                    'time': time,
                    'course': course,
                    'room': room,
                    'professor': professor
                })
        
        # Delete waiting message
        await wait_message.delete()
        
        # Format schedule message
        schedule_message = "📅 الجدول الدراسي:\n\n"
        current_day = None
        
        for item in schedule_data:
            if item['day'] != current_day:
                current_day = item['day']
                schedule_message += f"\n📌 {current_day}:\n"
            
            schedule_message += f"⏰ {item['time']} - {item['course']}\n"
            schedule_message += f"🏫 {item['room']} | 👨‍🏫 {item['professor']}\n"
        
        # Send the schedule
        await update.message.reply_text(
            f"{schedule_message}\n"
            "🔙 للعودة للقائمة الرئيسية، اختر أحد الخيارات التالية:"
        )
        log_request(user.id, user.username, "Schedule Request - Success", "SUCCESS", data={"schedule": schedule_data})
        
    except Exception as e:
        # Delete waiting message
        await wait_message.delete()
        await update.message.reply_text(
            "❌ حدث خطأ أثناء جلب الجدول الدراسي\n"
            "الرجاء المحاولة مرة أخرى لاحقاً"
        )
        log_request(user.id, user.username, f"Schedule Request - Error: {str(e)}", "FAILED") 