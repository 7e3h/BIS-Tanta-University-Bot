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
        login_page = session.get(LOGIN_URL, headers=headers)
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
        login_response = session.post(LOGIN_URL, data=login_data, headers=headers)
        logging.info(f"Login response status: {login_response.status_code}")
        print(f"\n=== حالة استجابة تسجيل الدخول: {login_response.status_code} ===")
        print(f"URL بعد تسجيل الدخول: {login_response.url}")

        # طباعة الـ cookies المستخرجة للتحقق
        print("\n=== الـ Cookies المستخرجة ===")
        print(f"Cookies: {dict(login_response.cookies)}")
        print(f"Set-Cookie header: {login_response.headers.get('Set-Cookie')}")

        # استخراج الـ cookies من الاستجابة
        session_id = None
        for cookie in login_response.cookies:
            if cookie.name == 'ASP.NET_SessionId':
                session_id = cookie.value
                break

        if session_id:
            headers['Cookie'] = f"ASP.NET_SessionId={session_id}"
            print(f"\n=== تم استخراج الـ Session ID: {session_id} ===")
        else:
            print("\n=== لم يتم العثور على ASP.NET_SessionId في الـ cookies ===")

        # حفظ الجلسة والـ headers في user_sessions
        user_sessions[user.id]['session'] = session
        user_sessions[user.id]['headers'] = headers
        
        # تحديث الـ Referer للصفحات التالية
        headers['Referer'] = 'https://tdb.tanta.edu.eg/ebooks/StudHome.aspx'

        if "StudHome.aspx" in login_response.url:
            # تم تسجيل الدخول بنجاح
            logging.info("Login successful, fetching books...")
            print("\n=== تم تسجيل الدخول بنجاح، جاري جلب الكتب... ===")
            
            # الحصول على صفحة الكتب
            home_page = session.get(HOME_URL, headers=headers)
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
                                    break  # نخرج من الحلقة بعد العثور على الرابط الأول
                        
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
    """Handle book selection callback."""
    query = update.callback_query
    await query.answer()
    
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
            # إنشاء جلسة جديدة إذا لم تكن موجودة
            session = requests.Session()
            session.verify = False
            
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
                'Referer': 'https://tdb.tanta.edu.eg/ebooks/StudHome.aspx',
                'Accept-Encoding': 'gzip, deflate, br',
                'Priority': 'u=0, i'
            }
            
            # تسجيل الدخول للحصول على الـ cookies
            login_page = session.get(LOGIN_URL, headers=headers)
            soup = BeautifulSoup(login_page.text, 'html.parser')
            
            viewstate = soup.find('input', {'name': '__VIEWSTATE'})['value']
            viewstategenerator = soup.find('input', {'name': '__VIEWSTATEGENERATOR'})['value']
            eventvalidation = soup.find('input', {'name': '__EVENTVALIDATION'})['value']
            
            login_data = {
                '__EVENTTARGET': '',
                '__EVENTARGUMENT': '',
                '__VIEWSTATE': viewstate,
                '__VIEWSTATEGENERATOR': viewstategenerator,
                '__SCROLLPOSITIONX': '0',
                '__SCROLLPOSITIONY': '0',
                '__EVENTVALIDATION': eventvalidation,
                'DDLFaculty': '8',
                'txtStudSSN': user_data['ssn'],
                'txtStudPW': user_data['password'],
                'loginButton': 'دخول'
            }
            
            login_response = session.post(LOGIN_URL, data=login_data, headers=headers)
            
            # طباعة الـ cookies المستخرجة للتحقق
            print("\n=== الـ Cookies المستخرجة ===")
            print(f"Cookies: {login_response.cookies}")
            print(f"Set-Cookie header: {login_response.headers.get('Set-Cookie')}")
            
            # استخراج الـ cookies من الاستجابة
            session_id = None
            for cookie in login_response.cookies:
                if cookie.name == 'ASP.NET_SessionId':
                    session_id = cookie.value
                    break
            
            if session_id:
                headers['Cookie'] = f"ASP.NET_SessionId={session_id}"
                print(f"\n=== تم استخراج الـ Session ID: {session_id} ===")
            else:
                print("\n=== لم يتم العثور على ASP.NET_SessionId في الـ cookies ===")
            
            # تخزين الجلسة في user_sessions
            user_sessions[query.from_user.id]['session'] = session
            user_sessions[query.from_user.id]['headers'] = headers
        
        # الحصول على صفحة الكتب للحصول على القيم المطلوبة
        home_page = session.get(HOME_URL, headers=user_sessions[query.from_user.id]['headers'])
        soup = BeautifulSoup(home_page.text, 'html.parser')
        
        # استخراج القيم المطلوبة
        viewstate = soup.find('input', {'name': '__VIEWSTATE'})['value']
        viewstategenerator = soup.find('input', {'name': '__VIEWSTATEGENERATOR'})['value']
        eventvalidation = soup.find('input', {'name': '__EVENTVALIDATION'})['value']
        
        print("\n=== القيم المستخرجة من الصفحة ===")
        print(f"VIEWSTATE: {viewstate[:100]}...")
        print(f"VIEWSTATEGENERATOR: {viewstategenerator}")
        print(f"EVENTVALIDATION: {eventvalidation[:100]}...")
        
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
        
        print("\n=== بيانات الطلب ===")
        print(json.dumps(post_data, indent=2, ensure_ascii=False))
        
        # إرسال الطلب
        response = session.post(HOME_URL, data=post_data, headers=user_sessions[query.from_user.id]['headers'])
        print(f"\n=== حالة الاستجابة: {response.status_code} ===")
        print(f"URL النهائي: {response.url}")
        print("\n=== محتوى الصفحة ===")
        print(response.text[:1000])  # طباعة أول 1000 حرف من محتوى الصفحة
        
        if response.url == COURSE_URL:
            # تم الانتقال إلى صفحة المادة بنجاح
            course_soup = BeautifulSoup(response.text, 'html.parser')
            
            # البحث عن روابط الكتب
            book_links = course_soup.find_all('a', href=lambda x: x and 'javascript:__doPostBack' in x)
            print(f"\n=== عدد روابط الكتب المستخرجة: {len(book_links)} ===")
            
            if book_links:
                keyboard = []
                for link in book_links:
                    # استخراج معرف الكتاب من الرابط
                    postback_match = re.search(r"__doPostBack\('([^']+)'", link['href'])
                    if postback_match:
                        book_id = postback_match.group(1)
                        # استخراج اسم الكتاب من النص
                        book_name = link.text.strip()
                        print(f"معرف الكتاب: {book_id}")
                        print(f"اسم الكتاب: {book_name}")
                        
                        # تجاهل زر تسجيل الخروج
                        if book_id != "LinkButton1":
                            keyboard.append([InlineKeyboardButton(book_name, callback_data=f"download_{book_id}")])
                
                if keyboard:
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    await query.message.edit_text(
                        "📚 الكتب المتاحة في المادة:",
                        reply_markup=reply_markup
                    )
                else:
                    print("\n=== لم يتم العثور على كتب متاحة ===")
                    await query.message.edit_text("❌ لم يتم العثور على كتب متاحة في هذه المادة")
            else:
                print("\n=== لم يتم العثور على روابط JavaScript للكتب ===")
                await query.message.edit_text("❌ لم يتم العثور على كتب متاحة في هذه المادة")
        else:
            print("\n=== فشل الانتقال إلى صفحة المادة ===")
            await query.message.edit_text("❌ حدث خطأ أثناء محاولة فتح صفحة المادة")
            
    except Exception as e:
        print(f"\n=== خطأ: {str(e)} ===")
        logging.error(f"Error during book selection: {str(e)}")
        await query.message.edit_text("❌ حدث خطأ أثناء محاولة فتح صفحة المادة")

async def handle_download_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle book download callback."""
    query = update.callback_query
    await query.answer()
    
    book_id = query.data.replace("download_", "")
    print(f"\n=== معرف الكتاب: {book_id} ===")
    
    try:
        # الحصول على جلسة المستخدم
        if query.from_user.id not in user_sessions:
            await query.message.edit_text("❌ يجب عليك تسجيل الدخول أولاً")
            return
            
        # استخدام الجلسة المخزنة للمستخدم
        user_data = user_sessions[query.from_user.id]
        session = user_data.get('session')
        headers = user_data.get('headers', {})
        
        if not session or not headers:
            await query.message.edit_text("❌ يجب عليك تسجيل الدخول مرة أخرى")
            return
        
        # الحصول على صفحة المادة للحصول على القيم المطلوبة
        print("\n=== جاري الحصول على صفحة المادة... ===")
        course_page = session.get(COURSE_URL, headers=headers)
        print(f"حالة صفحة المادة: {course_page.status_code}")
        
        soup = BeautifulSoup(course_page.text, 'html.parser')
        
        # استخراج القيم المطلوبة
        viewstate = soup.find('input', {'name': '__VIEWSTATE'})['value']
        viewstategenerator = soup.find('input', {'name': '__VIEWSTATEGENERATOR'})['value']
        eventvalidation = soup.find('input', {'name': '__EVENTVALIDATION'})['value']
        
        print("\n=== القيم المستخرجة من الصفحة ===")
        print(f"VIEWSTATE: {viewstate[:100]}...")
        print(f"VIEWSTATEGENERATOR: {viewstategenerator}")
        print(f"EVENTVALIDATION: {eventvalidation[:100]}...")
        
        # تجهيز بيانات الطلب
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
        
        print("\n=== بيانات الطلب ===")
        print(json.dumps(post_data, indent=2, ensure_ascii=False))
        
        # إرسال الطلب
        print("\n=== جاري إرسال طلب التحميل... ===")
        print("Headers:", headers)
        print("URL:", COURSE_URL)
        print("Post Data:", post_data)
        
        response = session.post(COURSE_URL, data=post_data, headers=user_sessions[query.from_user.id]['headers'])
        print(f"حالة الاستجابة: {response.status_code}")
        print(f"URL النهائي: {response.url}")
        print(f"Headers: {dict(response.headers)}")
        
        # التحقق من نوع المحتوى في الاستجابة
        content_type = response.headers.get('Content-Type', '')
        print(f"نوع المحتوى: {content_type}")
        
        if 'application/pdf' in content_type:
            # الاستجابة تحتوي على ملف PDF مباشرة
            print("\n=== تم العثور على ملف PDF مباشرة في الاستجابة ===")
            
            # استخراج اسم الملف من رأس Content-Disposition
            content_disposition = response.headers.get('Content-Disposition', '')
            print(f"Content-Disposition: {content_disposition}")
            
            file_name = "book.pdf"  # اسم افتراضي
            if 'filename=' in content_disposition:
                file_name = content_disposition.split('filename=')[1].strip('"')
            
            print(f"اسم الملف: {file_name}")
            
            # حفظ الملف مؤقتاً
            with tempfile.NamedTemporaryFile(delete=False, suffix=f"_{file_name}") as temp_file:
                temp_file.write(response.content)
                temp_file_path = temp_file.name
                print(f"تم حفظ الملف مؤقتاً في: {temp_file_path}")
            
            # إرسال الملف للمستخدم
            with open(temp_file_path, 'rb') as file:
                await query.message.reply_document(
                    document=file,
                    filename=file_name,
                    caption="📚 تم تحميل الكتاب بنجاح"
                )
            
            # حذف الملف المؤقت
            os.unlink(temp_file_path)
            print("تم حذف الملف المؤقت")
        else:
            # الاستجابة لا تحتوي على ملف PDF
            print("\n=== الاستجابة لا تحتوي على ملف PDF ===")
            print("محتوى الصفحة:")
            print(response.text[:1000])  # طباعة أول 1000 حرف من محتوى الصفحة
            await query.message.edit_text("❌ عذراً، الملف غير موجود")
            
    except Exception as e:
        print(f"\n=== خطأ: {str(e)} ===")
        logging.error(f"Error during book download: {str(e)}")
        await query.message.edit_text("❌ حدث خطأ أثناء محاولة تحميل الكتاب") 