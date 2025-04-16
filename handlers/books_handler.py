import logging
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ContextTypes
from utils.logger import log_request
import requests
from bs4 import BeautifulSoup
import json
from utils.shared_data import user_sessions
import urllib3
import ssl
import re
import os
import tempfile
from urllib.parse import urljoin

# تعطيل تحذيرات SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# تفعيل تسجيل الـ Logging
logging.basicConfig(level=logging.INFO)

# URLs
LOGIN_URL = "https://tdb.tanta.edu.eg/ebooks/Stud_login.aspx"
HOME_URL = "https://tdb.tanta.edu.eg/ebooks/StudHome.aspx"
COURSE_URL = "https://tdb.tanta.edu.eg/ebooks/StudCourseHome.aspx"

async def handle_books(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the books request."""
    user = update.effective_user
    log_request(user.id, user.username, "Books Request")

    # إضافة زر الرجوع في شريط الكتابة
    reply_keyboard = [[KeyboardButton("🔙 رجوع")]]
    reply_markup_keyboard = ReplyKeyboardMarkup(reply_keyboard, resize_keyboard=True)

    try:
        # التحقق من تسجيل دخول المستخدم
        if user.id not in user_sessions:
            await update.message.reply_text(
                "❌ يجب عليك تسجيل الدخول أولاً\n"
                "اضغط /start للبدء",
                reply_markup=reply_markup_keyboard
            )
            return

        # الحصول على بيانات المستخدم
        user_data = user_sessions[user.id]
        national_id = user_data['ssn']
        password = user_data['password']
        
        print(f"\n=== محاولة تسجيل الدخول للمستخدم {user.id} ===")
        print(f"الرقم القومي: {national_id}")

        # إنشاء جلسة جديدة
        session = requests.Session()
        session.verify = False  # تعطيل التحقق من شهادة SSL
        
        # إضافة الـ headers المطلوبة
        headers = {
            'Host': 'tdb.tanta.edu.eg',
            'Cache-Control': 'max-age=0',
            'Sec-Ch-Ua': '"Brave";v="135", "Not-A.Brand";v="8", "Chromium";v="135"',
            'Sec-Ch-Ua-Mobile': '?0',
            'Sec-Ch-Ua-Platform': '"Windows"',
            'Upgrade-Insecure-Requests': '1',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36',
            'Origin': 'https://tdb.tanta.edu.eg',
            'Content-Type': 'application/x-www-form-urlencoded',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Sec-Gpc': '1',
            'Accept-Language': 'en-US,en;q=0.8',
            'Sec-Fetch-Site': 'same-origin',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-User': '?1',
            'Sec-Fetch-Dest': 'document',
            'Referer': 'https://tdb.tanta.edu.eg/ebooks/Stud_login.aspx',
            'Accept-Encoding': 'gzip, deflate, br',
            'Priority': 'u=0, i'
        }

        # الحصول على VIEWSTATE وغيرها من القيم
        print("\n=== جاري الحصول على صفحة تسجيل الدخول... ===")
        login_page = session.get(LOGIN_URL)
        print(f"حالة صفحة تسجيل الدخول: {login_page.status_code}")
        
        soup = BeautifulSoup(login_page.text, 'html.parser')
        
        # استخراج القيم المطلوبة
        viewstate = soup.find('input', {'name': '__VIEWSTATE'})['value']
        viewstategenerator = soup.find('input', {'name': '__VIEWSTATEGENERATOR'})['value']
        eventvalidation = soup.find('input', {'name': '__EVENTVALIDATION'})['value']
        
        print("\n=== القيم المستخرجة من صفحة تسجيل الدخول ===")
        print(f"VIEWSTATE: {viewstate[:100]}...")
        print(f"VIEWSTATEGENERATOR: {viewstategenerator}")
        print(f"EVENTVALIDATION: {eventvalidation[:100]}...")
        
        # تجهيز بيانات تسجيل الدخول
        login_data = {
            '__EVENTTARGET': '',
            '__EVENTARGUMENT': '',
            '__VIEWSTATE': viewstate,
            '__VIEWSTATEGENERATOR': viewstategenerator,
            '__SCROLLPOSITIONX': '0',
            '__SCROLLPOSITIONY': '0',
            '__EVENTVALIDATION': eventvalidation,
            'DDLFaculty': '8',  # رقم كلية التجارة
            'txtStudSSN': national_id,
            'txtStudPW': password,
            'loginButton': 'دخول'
        }
        
        print("\n=== بيانات تسجيل الدخول ===")
        print(json.dumps(login_data, indent=2, ensure_ascii=False))
        
        # محاولة تسجيل الدخول
        logging.info("Attempting login...")
        login_response = session.post(LOGIN_URL, data=login_data,)
        logging.info(f"Login response status: {login_response.status_code}")
        print(f"\n=== حالة استجابة تسجيل الدخول: {login_response.status_code} ===")
        print(f"URL بعد تسجيل الدخول: {login_response.url}")

        # طباعة الـ cookies المستخرجة للتحقق
        print("\n=== الـ Cookies المستخرجة ===")
        print(f"Cookies: {dict(login_response.cookies)}")
        print(f"Set-Cookie header: {login_response.headers.get('Set-Cookie')}")

        # حفظ الجلسة في user_sessions
        user_sessions[user.id]['session'] = session
        
        # تحديث الـ Referer للصفحات التالية
        headers['Referer'] = 'https://tdb.tanta.edu.eg/ebooks/StudHome.aspx'

        if "StudHome.aspx" in login_response.url:
            # تم تسجيل الدخول بنجاح
            logging.info("Login successful, fetching books...")
            print("\n=== تم تسجيل الدخول بنجاح، جاري جلب الكتب... ===")
            
            # الحصول على صفحة الكتب
            home_page = session.get(HOME_URL)
            books_soup = BeautifulSoup(home_page.text, 'html.parser')
            
            # استخراج أسماء المواد وروابطها
            books = books_soup.find_all('div', class_='brows-job-list')
            print(f"\n=== عدد الكتب المستخرجة: {len(books)} ===")
            
            if books:
                keyboard = []
                for book in books:
                    # استخراج عنوان الكتاب
                    title_element = book.find('h3')
                    if title_element:
                        title = title_element.text.strip()
                        print(f"عنوان الكتاب: {title}")
                        
                        # البحث عن رابط JavaScript في عنصر brows-job-link
                        link_divs = book.find_all('div', class_='brows-job-link')
                        for link_div in link_divs:
                            link = link_div.find('a', href=lambda x: x and 'javascript:__doPostBack' in x)
                            if link:
                                print(f"رابط الكتاب: {link['href']}")
                                # استخراج معرف المادة من الرابط
                                postback_match = re.search(r"__doPostBack\('([^']+)'", link['href'])
                                if postback_match:
                                    subject_id = postback_match.group(1)
                                    print(f"معرف المادة: {subject_id}")
                                    keyboard.append([InlineKeyboardButton(title, callback_data=f"book_{subject_id}")])
                                    break
                                      # نخرج من الحلقة بعد العثور على الرابط الأول
                        
                if keyboard:
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    await update.message.reply_text(
                        "📚 الكتب الدراسية المتاحة:",
                        reply_markup=reply_markup
                    )
                else:
                    print("\n=== لم يتم العثور على روابط JavaScript للكتب ===")
                    await update.message.reply_text(
                        "❌ لم يتم العثور على كتب متاحة",
                        reply_markup=reply_markup_keyboard
                    )
            else:
                print("\n=== لم يتم العثور على كتب متاحة ===")
                print("محتوى الصفحة:")
                print(books_soup.prettify()[:1000])  # طباعة أول 1000 حرف من محتوى الصفحة
                
                await update.message.reply_text(
                    "❌ لم يتم العثور على كتب متاحة",
                    reply_markup=reply_markup_keyboard
                )
        else:
            print("\n=== فشل تسجيل الدخول ===")
            print("محتوى صفحة الخطأ:")
            print(login_response.text[:1000])  # طباعة أول 1000 حرف من محتوى الصفحة
            
            await update.message.reply_text(
                "❌ خطأ في تسجيل الدخول. تأكد من صحة البيانات",
                reply_markup=reply_markup_keyboard
            )
        
    except Exception as e:
        print(f"\n=== خطأ: {str(e)} ===")
        logging.error(f"Error during login: {str(e)}")
        await update.message.reply_text(
            "❌ حدث خطأ أثناء محاولة تسجيل الدخول",
            reply_markup=reply_markup_keyboard
        )

async def handle_book_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle book selection callback and download book directly."""
    query = update.callback_query
    await query.answer()
    print(f"data:{query.data}")
    subject_id = query.data.replace("book_", "")
    print(f"\n=== معرف المادة: {subject_id} ===")
    
    try:
        # الحصول على جلسة المستخدم
        if query.from_user.id not in user_sessions:
            await query.message.edit_text("❌ يجب عليك تسجيل الدخول أولاً")
            return
            
        # الحصول على جلسة المستخدم المخزنة
        user_data = user_sessions[query.from_user.id]
        session = user_data.get('session')
        
        if not session:
            await query.message.edit_text("❌ يجب عليك تسجيل الدخول مرة أخرى")
            return
        
        # الحصول على صفحة الكتب للحصول على القيم المطلوبة
        home_page = session.get(HOME_URL)
        soup = BeautifulSoup(home_page.text, 'html.parser')
        
        # استخراج القيم المطلوبة
        viewstate = soup.find('input', {'name': '__VIEWSTATE'})['value']
        viewstategenerator = soup.find('input', {'name': '__VIEWSTATEGENERATOR'})['value']
        eventvalidation = soup.find('input', {'name': '__EVENTVALIDATION'})['value']
        
        # تجهيز بيانات الطلب
        post_data = {
            '__EVENTTARGET': subject_id,
            '__EVENTARGUMENT': '',
            '__VIEWSTATE': viewstate,
            '__VIEWSTATEGENERATOR': viewstategenerator,
            '__SCROLLPOSITIONX': '0',
            '__SCROLLPOSITIONY': '900',
            '__EVENTVALIDATION': eventvalidation,
            'hdnBookTotalPrices': ''
        }
        
        # إرسال الطلب للانتقال لصفحة المادة
        response = session.post(HOME_URL, data=post_data)
        print(f"\n=== حالة الاستجابة: {response.status_code} ===")
        print(f"URL النهائي: {response.url}")
        
        if response.url == COURSE_URL:
            # تم الانتقال إلى صفحة المادة بنجاح
            course_soup = BeautifulSoup(response.text, 'html.parser')
            # البحث عن روابط الكتب
            book_links = course_soup.find_all('a', href=lambda x: x and 'javascript:__doPostBack' in x)
            print(f"\n=== عدد روابط الكتب المستخرجة: {len(book_links)} ===")
            
            if book_links:
                # تحميل كل الكتب المتاحة في المادة مع تجاهل LinkButton1
                first_sent = False
                for link in book_links:
                    postback_match = re.search(r"__doPostBack\('([^']+)'", link['href'])
                    if postback_match:
                        book_id = postback_match.group(1)
                        if book_id == "LinkButton1":
                            continue  # تجاهل هذا الكتاب ولا تحمله
                        # استخراج القيم المطلوبة من صفحة المادة (يجب تحديثها كل مرة)
                        viewstate = course_soup.find('input', {'name': '__VIEWSTATE'})['value']
                        viewstategenerator = course_soup.find('input', {'name': '__VIEWSTATEGENERATOR'})['value']
                        eventvalidation = course_soup.find('input', {'name': '__EVENTVALIDATION'})['value']
                        post_data = {
                            '__EVENTTARGET': book_id,
                            '__EVENTARGUMENT': '',
                            '__VIEWSTATE': viewstate,
                            '__VIEWSTATEGENERATOR': viewstategenerator,
                            '__SCROLLPOSITIONX': '0',
                            '__SCROLLPOSITIONY': '0',
                            '__VIEWSTATEENCRYPTED': '',
                            '__EVENTVALIDATION': eventvalidation
                        }
                        headers = {
                            'Host': 'tdb.tanta.edu.eg',
                            'Connection': 'keep-alive',
                            'Cache-Control': 'max-age=0',
                            'Upgrade-Insecure-Requests': '1',
                            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36',
                            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
                            'Sec-Fetch-Site': 'same-origin',
                            'Sec-Fetch-Mode': 'navigate',
                            'Sec-Fetch-User': '?1',
                            'Sec-Fetch-Dest': 'document',
                            'Referer': COURSE_URL,
                            'Accept-Encoding': 'gzip, deflate, br',
                            'Accept-Language': 'en-US,en;q=0.9',
                            'Content-Type': 'application/x-www-form-urlencoded'
                        }
                        # تحديث رسالة المستخدم مرة واحدة فقط قبل أول تحميل
                        if not first_sent:
                            await query.message.edit_text("⏳ جاري تحميل الكتب...")
                            first_sent = True
                        # إرسال الطلب لتحميل الكتاب
                        book_response = session.post(COURSE_URL, data=post_data, headers=headers)
                        print(f'{book_response.text}')
                        print(f'{post_data}')
                        content_type = book_response.headers.get('Content-Type', '')
                        if 'application/pdf' in content_type:
                            content_disposition = book_response.headers.get('Content-Disposition', '')
                            file_name = "book.pdf"
                            if 'filename=' in content_disposition:
                                file_name = content_disposition.split('filename=')[1].strip('"')
                                # تنظيف اسم الملف من الرموز غير الصالحة
                                file_name = re.sub(r'[\\/*?:"<>|]', "", file_name)
                            with tempfile.NamedTemporaryFile(delete=False, suffix=f"_{file_name}") as temp_file:
                                temp_file.write(book_response.content)
                                temp_file_path = temp_file.name
                            with open(temp_file_path, 'rb') as file:
                                await context.bot.send_document(
                                    chat_id=query.from_user.id,
                                    document=file,
                                    filename=file_name,
                                    caption=f"📚 تم تحميل الكتاب: {link.text.strip()}"
                                )
                            os.unlink(temp_file_path)
                        else:
                            soup2 = BeautifulSoup(book_response.text, 'html.parser')
                            download_link = soup2.find('a', {'id': lambda x: x and x.endswith('LinkButton2')})
                            if download_link and download_link.get('href'):
                                file_url = urljoin(COURSE_URL, download_link['href'])
                                file_response = session.get(file_url, headers=headers)
                                with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
                                    temp_file.write(file_response.content)
                                    temp_path = temp_file.name
                                with open(temp_path, 'rb') as file:
                                    await context.bot.send_document(
                                        chat_id=query.from_user.id,
                                        document=file,
                                        filename='book.pdf',
                                        caption=f"📚 تم تحميل الكتاب: {link.text.strip()}"
                                    )
                                os.unlink(temp_path)
                            else:
                                await context.bot.send_message(
                                    chat_id=query.from_user.id,
                                    text=f"❌ لم يتم العثور على رابط التحميل للكتاب: {link.text.strip()}"
                                )
                # بعد الانتهاء من إرسال كل الكتب، أرسل رسالة جديدة بدلاً من تعديل نفس الرسالة
                await context.bot.send_message(
                    chat_id=query.from_user.id,
                    text="✅ تم تحميل جميع الكتب المتاحة!\nاختر مادة أخرى أو عد للقائمة الرئيسية:",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("🔙 رجوع", callback_data="main_menu")
                    ]])
                )
            else:
                await query.message.edit_text("❌ لم يتم العثور على كتب متاحة في هذه المادة")
        else:
            await query.message.edit_text("❌ حدث خطأ أثناء محاولة فتح صفحة المادة")
        
    except Exception as e:
        print(f"\n=== خطأ: {str(e)} ===")
        logging.error(f"Error during book selection/download: {str(e)}")
        await query.message.edit_text(
            "❌ حدث خطأ أثناء محاولة تحميل الكتاب",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 رجوع", callback_data="main_menu")
            ]])
        )