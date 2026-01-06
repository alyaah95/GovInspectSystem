# تثبيت المكتبات الموجودة في requirements.txt
pip install -r requirements.txt

# تجميع ملفات الـ CSS والـ JS (Static Files)
python3.9 manage.py collectstatic --noinput

# (اختياري) تنفيذ الميجريشن إذا كنتِ ربطتِ قاعدة البيانات بنجاح
python3.9 manage.py migrate --noinput