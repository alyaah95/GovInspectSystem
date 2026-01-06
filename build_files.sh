#!/bin/bash

echo "--- BUILD START ---"

# التأكد من وجود pip وتحديثه
python3.9 -m ensurepip
python3.9 -m pip install --upgrade pip

# تثبيت المكتبات (أهم تعديل هو --user أو المسار الحالي)
python3.9 -m pip install -r requirements.txt

# جمع الملفات الثابتة
python3.9 manage.py collectstatic --noinput --clear

echo "--- BUILD END ---"