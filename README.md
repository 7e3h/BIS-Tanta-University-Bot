# بوت تحميل الكتب الدراسية - جامعة طنطا 📚

# بوت تليجرام مخصص لمساعده طلاب نظم ومعلومات الاعمال جامعه طنطا يساعدهم في الحصول علي كل خدمات الجامعه مع مميزات اضافيه في مكان واحد بواجهه سهله وبسيطه 

## المميزات 🌟

- **تسجيل الدخول الآمن**: 
  - تسجيل الدخول باستخدام الرقم القومي وكلمة المرور
  - حماية البيانات وعدم تخزينها بشكل دائم
  - جلسة مستقلة لكل مستخدم

- **واجهة مستخدم متطورة**:
  - أزرار تفاعلية سهلة الاستخدام
  - قوائم منسدلة للاختيار السريع
  - رسائل تأكيد وتنبيه واضحة
  - دعم كامل للغة العربية

- **إدارة الكتب والمحتوى التعليمي**:
  - عرض قائمة الكتب المتاحة بشكل منظم
  - تحميل الكتب مباشرة على تيليجرام
  - عرض حالة التحميل في الوقت الفعلي
  - إمكانية إلغاء التحميل
  - الوصول للملخصات والمذكرات الدراسية
  - عرض نتائج الامتحانات
  - إدارة البريد الجامعي

## الأزرار والوظائف 🎯

### أزرار البداية
- **/start**: بدء استخدام البوت وعرض القائمة الرئيسية
- **🔙 رجوع**: العودة للقائمة السابقة في أي وقت

### القائمة الرئيسية
- **📚 الكتب الدراسية**: عرض قائمة الكتب المتاحة
- **📝 الملخصات**: عرض وتحميل الملخصات والمذكرات الدراسية
- **📊 نتائج الامتحانات**: الاستعلام عن نتائج الامتحانات
- **📧 البريد الجامعي**: إدارة البريد الإلكتروني الجامعي
- **🔄 تسجيل خروج**: إنهاء الجلسة الحالية

### أزرار الكتب
- **📖 عرض الكتاب**: عرض تفاصيل الكتاب المحدد
- **⬇️ تحميل**: بدء تحميل الكتاب المحدد
- **❌ إلغاء**: إلغاء عملية التحميل

### أزرار الملخصات
- **📋 عرض الملخصات**: عرض قائمة الملخصات المتاحة
- **⬇️ تحميل الملخص**: تحميل الملخص المحدد
- **📤 رفع ملخص**: إضافة ملخص جديد (للمشرفين)

### أزرار نتائج الامتحانات
- **🔍 استعلام**: البحث عن نتيجة امتحان معين
- **⬇️ تحميل كشف الدرجات**: تحميل كشف الدرجات كامل

### أزرار البريد الجامعي
- **📨الحصول علي البريد الجامعي**: استراد البريد الخاص بكل طالب وكلمه مروره
## المتطلبات الفنية 📋

### متطلبات النظام
- Python 3.7 أو أحدث
- ذاكرة RAM: 512MB على الأقل
- مساحة تخزين: 100MB على الأقل
- اتصال إنترنت مستقر

### متطلبات المستخدم
- حساب على موقع جامعة طنطا للكتب الدراسية
- الرقم القومي وكلمة المرور
- تطبيق تيليجرام

### متطلبات البوت
- توكن بوت تيليجرام (يمكن الحصول عليه من @BotFather)
- صلاحيات إرسال الملفات على تيليجرام

## التثبيت والإعداد ⚙️

### 1. تجهيز البيئة
```bash
# إنشاء بيئة افتراضية (اختياري ولكن مستحسن)
python -m venv venv

# تفعيل البيئة الافتراضية
# Windows
venv\Scripts\activate
# Linux/Mac
source venv/bin/activate
```

### 2. تثبيت المكتبات
```bash
# تثبيت المكتبات المطلوبة
pip install -r requirements.txt
```

### 3. إعداد ملف البيئة
قم بإنشاء ملف `.env` في المجلد الرئيسي وأضف:
```env
# توكن البوت الخاص بك
BOT_TOKEN=your_bot_token_here

# إعدادات اختيارية
DEBUG=True  # لتفعيل وضع التصحيح
LOG_LEVEL=INFO  # مستوى التسجيل
```

### 4. تشغيل البوت
```bash
# تشغيل البوت
python main.py
```

## هيكل المشروع التفصيلي 📁

```
BIS_BOT/
├── main.py                 # نقطة البداية للبوت
│   ├── تهيئة البوت
│   ├── إعداد المعالجات
│   └── تشغيل البوت
│
├── handlers/
│   |── books_handler.py    # معالج الكتب
│   |── email_handler.py    # معالج البريد الجامعي
|   |── attendance_handler.py # الحضور والغياب جار العمل عليه
|   |── login_handler.py    # تسجيل دخول الطالب
|   |── logout_handler.py   # تسجيل الخروج  
|   |── results_handler.py  # نتائج الامتحنات (GPA فقط)
|   |── schedule_handler.py # الجدول الدراسي جار العمل عليه
|   |── summaries_handler.py # الحصول علي ملخصات لمساعده الطالب 
|   └── AI.py               # قسم مخصص للذكاء الاصطناعي لمساعده الطالب علي فهم المحاضرات وحل المسائل جار العمل عليه
|
|
├── summaries/
|   └── المكان المخصص لحفظ الملخصات
|
├── utils/
│   ├── logger.py          # وحدة التسجيل
│   │   ├── إعداد التسجيل
│   │   └── تنسيق الرسائل
│   │
│   └── shared_data.py     # البيانات المشتركة
│       ├── user_sessions  # جلسات المستخدمين
│
├── requirements.txt       # المكتبات المطلوبة
└── .env                  # ملف الإعدادات
```

## المكتبات المستخدمة وأدوارها 📚

### python-telegram-bot (20.8)
- إنشاء وإدارة البوت
- معالجة الأوامر والأزرار
- إرسال واستقبال الملفات
- إدارة المحادثات
- معالجة الردود التفاعلية
- إدارة لوحات المفاتيح المخصصة

### requests (2.31.0)
- الاتصال بموقع الجامعة
- إرسال طلبات تسجيل الدخول
- تحميل الكتب والملخصات
- إدارة الجلسات
- التعامل مع البريد الإلكتروني
- الاستعلام عن النتائج

### beautifulsoup4 (4.12.3)
- تحليل صفحات الويب
- استخراج روابط الكتب
- استخراج معلومات الكتب
- معالجة النصوص العربية

### python-dotenv (1.0.1)
- قراءة ملف الإعدادات
- حماية المعلومات الحساسة
- إدارة متغيرات البيئة

### urllib3 (2.2.1)
- إدارة الاتصالات الآمنة
- التعامل مع الشهادات
- إدارة التحميل

## الأمان والخصوصية 🔒

### حماية البيانات
- تشفير جميع الاتصالات مع موقع الجامعة
- عدم تخزين كلمات المرور
- مسح البيانات عند تسجيل الخروج

### إدارة الجلسات
- جلسة مستقلة لكل مستخدم
- تجديد الجلسات تلقائياً
- إنهاء الجلسات غير النشطة

### حماية من الاختراق
- التحقق من صحة المدخلات
- منع محاولات الاختراق
- تسجيل جميع العمليات

## حل المشكلات الشائعة 🔧

### مشاكل تسجيل الدخول
- التأكد من صحة الرقم القومي وكلمة المرور
- التحقق من اتصال الإنترنت
- محاولة تسجيل الخروج وإعادة الدخول
- التأكد من صلاحية حساب البريد الجامعي

### مشاكل البريد الإلكتروني
- الحصول علي البريد الجامعي وكلمه المرور لكل طالب بطريقه امنه تمام

### مشاكل نتائج الامتحانات
- التأكد من إتاحة النتائج
- عرض نتائج الطلاب (GPA فقط)

### مشاكل عامة
- إعادة تشغيل البوت
- مسح ذاكرة التخزين المؤقت
- تحديث تيليجرام

## المساهمة في التطوير 🤝

### خطوات المساهمة
1. عمل Fork للمشروع
2. إنشاء فرع جديد للميزة
   ```bash
   git checkout -b feature/new-feature
   ```
3. تطوير الميزة وإضافة الاختبارات
4. عمل Commit للتغييرات
   ```bash
   git commit -m "إضافة: وصف الميزة الجديدة"
   ```
5. رفع التغييرات
   ```bash
   git push origin feature/new-feature
   ```
6. إنشاء Pull Request

### معايير الكود
- اتباع معايير PEP 8
- كتابة تعليقات واضحة
- توثيق الدوال والفئات
- إضافة اختبارات للكود

## الترخيص والحقوق 📄

هذا المشروع مرخص تحت [MIT License](LICENSE).

### الحقوق
- حقوق البوت محفوظة للمطور
- حقوق الكتب محفوظة لجامعة طنطا
- يمنع الاستخدام التجاري

### شروط الاستخدام
- الاستخدام الشخصي فقط
- عدم إعادة توزيع الكتب
- الالتزام بشروط جامعة طنطا 
**Bot Developer: Omar El-Saaty**
**TeleGram :@B3NXX**