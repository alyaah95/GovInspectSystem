#!/bin/bash

echo "--- BUILD START ---"

# تثبيت المكتبات باستخدام pip مباشرة
pip install -r requirements.txt

# إنشاء المجلد المطلوب يدوياً للتأكد من وجوده حتى لو فشل الأمر التالي
mkdir -p staticfiles_build/static

# تجميع الملفات الثابتة
python3.9 manage.py collectstatic --noinput --clear

echo "--- BUILD END ---"