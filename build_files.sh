#!/bin/bash

echo "--- BUILD START ---"

# استخدام بايثون لتثبيت المكتبات بشكل يضمن وجودها في المسار الصحيح
python3.9 -m ensurepip
python3.9 -m pip install -r requirements.txt

# جمع الملفات الثابتة
python3.9 manage.py collectstatic --noinput --clear

echo "--- BUILD END ---"