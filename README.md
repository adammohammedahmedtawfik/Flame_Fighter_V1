# 🔥 Flame Fighter - Tactical Defense Station

> **Autonomous AI Fire & Electrical Hazard Suppression System**  
> Standalone production station running real-time YOLOv8 computer vision detection, distance/hazard analytics, and automated multi-pump actuation (Water & Foam) via Arduino USB and Raspberry Pi bridge.

---

## ⚡ Quick Start (تشغيل فوري بضغطة واحدة)

فقط اضغط دبل كليك على:
```cmd
run.bat
```
يقوم الملف تلقائياً بـ:
1. تحرير منفذ `5000` والتأكد من عدم وجود جلسات سابقة معلقة.
2. فحص كاميرات الـ USB الخارجية وتفضيلها تلقائياً على كاميرا اللابتوب الداخلية.
3. فتح لوحة التحكم التكتيكية في المتصفح تلقائياً على `http://localhost:5000`.
4. تشغيل خادم الاستدلال والتحكم الذكي `System_IP.py`.

---

## 📁 هيكل المشروع المستقل (Standalone Architecture)

```
Flame-Fighter-Live/
│
├── run.bat                          # مشغل المحطة التكتيكية بنقرة واحدة
├── push_to_github.bat               # أداة المزامنة والرفع التلقائي إلى GitHub
├── System_IP.py                     # الخادم الأساسي ومعالجة الكاميرا والذكاء الاصطناعي
├── rpi_server.py                    # خادم الراسبيري باي للتحكم في الريلاي (GPIO Relay)
├── requirements.txt                 # مكتبات بايثون المطلوبة
├── .gitignore                       # استثناء الملفات المؤقتة وحفظ الأوزان
│
├── runs/detect/                     # نماذج الذكاء الاصطناعي المدربة (YOLO Weights)
│   ├── finetune_v1/weights/best.pt          # نموذج كشف ألسنة اللهب (Fire Model)
│   └── electric_finetune_v1/weights/best.pt # نموذج كشف المقابس والفيش (Socket Model)
│
├── templates/
│   ├── Doma_flame_fighter_UI.html   # لوحة التحكم التكتيكية OLED Tactical UI
│   └── CinzelDecorative-Bold.ttf
│
└── static/                          # الخطوط وعناصر التصميم
    ├── Cairo-Bold.ttf
    ├── CinzelDecorative-Bold.ttf
    └── Orbitron-Bold.ttf
```

---

## 🛠️ التثبيت اليدوي (Manual Setup)

إذا كنت تقوم بتشغيل المشروع لأول مرة على جهاز جديد:

1. **تثبيت المتطلبات**:
```bash
pip install -r requirements.txt
```

2. **التشغيل المباشر عبر بايثون**:
```bash
python System_IP.py
```
> اختياري: لتحديد كاميرا معينة يدوياً: `python System_IP.py --cam 1`

---

## 🤖 منطق اتخاذ القرار التكتيكي (Tactical Decision Matrix)

1. **NO FIRE**: إيقاف تشغيل المضخات فوراً (`STOP_ALL`).
2. **WATER PUMP**: حريق معزول بعيداً عن مصادر الكهرباء (المسافة > 140px / منطقة أمان).
3. **FOAM PUMP**: حريق داخل منطقة الخطر الكهربائي (المسافة ≤ 140px من المقبس / الفيشة الكهربائية لمنع الصعق).

---

## 🔌 المنافذ وواجهة البرمجة (REST & Streaming Endpoints)

| Endpoint | Method | الوصف |
| :--- | :--- | :--- |
| `/` | `GET` | واجهة المستخدم التكتيكية التفاعلية |
| `/video_feed` | `GET` | بث فيديو مباشر فائق السرعة MJPEG مع المربعات والاحتماليات |
| `/api/detection` | `GET` | بيانات JSON لحظية (إحداثيات الحريق، المسافة بالسنتيمتر، والقرار) |
| `/health` | `GET` | فحص حالة النظام، الكاميرا المتصلة، ونماذج الذكاء الاصطناعي |

---

## 📡 التوصيل بالعتاد (Hardware Setup)

- **Arduino USB**: يتم التعرف على منفذ الـ COM تلقائياً وإرسال الأوامر التسلسلية (`WATER_ON`, `FOAM_ON`, `STOP_ALL`) بمعدل Baud Rate 9600.
- **Raspberry Pi Bridge**: في حال عدم وجود كابل USB متصل مباشرة، يوجه النظام الأوامر تلقائياً عبر الشبكة المحلية إلى `rpi_server.py`.
