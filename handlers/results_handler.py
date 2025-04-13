import os
import time
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ContextTypes
from utils.shared_data import user_sessions
from utils.logger import log_request
from io import BytesIO

# Load environment variables
load_dotenv()

async def handle_results(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the exam results request."""
    user = update.effective_user
    log_request(user.id, user.username, "Results Request")

    # Check if user is authenticated
    if user.id not in user_sessions:
        await update.message.reply_text(
            "❌ عذراً، يجب عليك تسجيل الدخول أولاً\n"
            "اضغط /start للبدء"
        )
        log_request(user.id, user.username, "Results Request - Not Authenticated", "FAILED")
        return

    # Create back button
    keyboard = [["🔙 رجوع"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    # Show waiting message
    wait_message = await update.message.reply_text(
        "⏳ جاري جلب نتائج الامتحانات...",
        reply_markup=reply_markup
    )

    try:
        user_data = user_sessions[user.id]
        ssn = user_data['ssn']

        session = requests.Session()
        session.verify = False

        login_url = "https://tdb.tanta.edu.eg/commonline/default.aspx"
        result_url = "https://tdb.tanta.edu.eg/commonline/print_sem_result.aspx"
        base_url = "https://tdb.tanta.edu.eg"

        # Step 1: Get login form
        print("\n=== LOGIN PAGE REQUEST ===")
        login_page = session.get(login_url)
        print(f"URL: {login_url}")
        print(f"Status Code: {login_page.status_code}")
        print(f"Response Headers: {dict(login_page.headers)}")
        print(f"Response Content (first 1000 chars):\n{login_page.text}")
        
        soup = BeautifulSoup(login_page.text, 'html.parser')

        viewstate = soup.find('input', {'name': '__VIEWSTATE'})['value']
        viewstategenerator = soup.find('input', {'name': '__VIEWSTATEGENERATOR'})['value']
        eventvalidation = soup.find('input', {'name': '__EVENTVALIDATION'})['value']

        login_data = {
            '__EVENTTARGET': '',
            '__EVENTARGUMENT': '',
            '__LASTFOCUS': '',
            '__VIEWSTATE': viewstate,
            '__VIEWSTATEGENERATOR': viewstategenerator,
            '__EVENTVALIDATION': eventvalidation,
            'DDL_login': '3',
            'txtpart1': ssn,
            'Button2': 'دخول'
        }

        print("\n=== LOGIN REQUEST ===")
        print(f"URL: {login_url}")
        print(f"Data: {login_data}")
        login_response = session.post(login_url, data=login_data)
        print(f"Status Code: {login_response.status_code}")
        print(f"Response Headers: {dict(login_response.headers)}")
        print(f"Response Content (first 1000 chars):\n{login_response.text}")

        # Step 2: Go to results page
        print("\n=== RESULTS PAGE REQUEST ===")
        res_page = session.get(result_url)
        print(f"URL: {result_url}")
        print(f"Status Code: {res_page.status_code}")
        print(f"Response Headers: {dict(res_page.headers)}")
        print(f"Response Content (first 1000 chars):\n{res_page.text}")
        
        soup = BeautifulSoup(res_page.text, 'html.parser')

        iframe = soup.find('iframe', {'id': 'ReportFramectl00_ContentPlaceHolder2_ReportViewer1'})
        if not iframe:
            raise Exception("لم يتم العثور على الـ iframe الأول")

        first_iframe_url = iframe['src']
        if not first_iframe_url.startswith('http'):
            first_iframe_url = base_url + first_iframe_url

        # Step 3: Access the first iframe content
        print("\n=== FIRST IFRAME REQUEST ===")
        print(f"URL: {first_iframe_url}")
        first_iframe_res = session.get(first_iframe_url)
        print(f"Status Code: {first_iframe_res.status_code}")
        print(f"Response Headers: {dict(first_iframe_res.headers)}")
        print(f"Response Content (first 1000 chars):\n{first_iframe_res.text}")
        
        soup = BeautifulSoup(first_iframe_res.text, 'html.parser')

        second_frame = soup.find('frame', {'id': 'report'})
        if not second_frame:
            raise Exception("لم يتم العثور على الـ iframe الثاني")

        second_iframe_url = second_frame['src']
        if not second_iframe_url.startswith('http'):
            second_iframe_url = base_url + second_iframe_url

        # Step 4: Get final GPA page
        print("\n=== SECOND IFRAME REQUEST ===")
        print(f"URL: {second_iframe_url}")
        headers1 = {
            'Cache-Control': 'no-cache'
        }
        final_page = session.get(second_iframe_url, headers=headers1, timeout=60)
        print(f"Status Code: {final_page.status_code}")
        print(f"Response Headers: {dict(final_page.headers)}")
        print(f"Response Content (first 1000 chars):\n{final_page.text}")
        
        # Wait a bit to ensure the page is fully loaded
        time.sleep(3)  # Waiting for 3 seconds to ensure the page is fully loaded

        # Extract GPA from the page
        soup = BeautifulSoup(final_page.text, 'html.parser')
        gpa_text = soup.get_text()
        
        # Use regex to find GPA value
        import re
        gpa_match = re.search(r'نتيجة\s+الفصل\s*:(\d+(?:\.\d+)?)', gpa_text)
        if not gpa_match:
            raise Exception("لم يتم العثور على المعدل الفصلي")
        
        gpa = gpa_match.group(1)
        print(f"\n=== EXTRACTED GPA: {gpa} ===")

        # Send GPA to user
        await update.message.reply_text(
            f"📊 المعدل الفصلي = {gpa}",
            reply_markup=reply_markup
        )

        await wait_message.delete()
        log_request(user.id, user.username, "Results Request - Success", "SUCCESS")

    except Exception as e:
        await wait_message.delete()
        await update.message.reply_text(
            "❌ حدث خطأ أثناء جلب النتائج، حاول لاحقاً",
            reply_markup=reply_markup
        )
        log_request(user.id, user.username, f"Results Request - Error: {str(e)}", "FAILED") 