from django import template
import json

register = template.Library()

# a dictionary to map technical field names to human-readable Arabic names
FIELD_NAMES = {
    # Company Fields (الموجودة سابقاً)
    'company_name': 'اسم المنشأة',
    'company_number': 'رقم المنشأة',
    'region': 'المنطقة',
    'street_name': 'اسم الشارع',
    'building_number': 'رقم العقار',
    'activity_type': 'نوع النشاط',
    'electricity_meter_number': 'رقم الكهرباء',
    'actual_workers_count': 'عدد العمال الفعلي',
    'establishment_type': 'نوع المنشأة',
    'size_description': 'وصف الحجم',
    'created_at': 'تاريخ الإضافة',
    'status': 'الحالة',
    'manager': 'المدير المسؤول',
    'assigned_to': 'المفتش المعين',
    'status_by_inspector': 'حالة التعيين',
    'decline_reason': 'سبب الرفض',
    
    # User Fields (the ones that are used in the User model)
    'phone_number': 'رقم الجوال',
    'address': 'العنوان',
    'user_id': 'رقم الهوية',
    'supervisor': 'المشرف/المدير',
    'username': 'اسم المستخدم',
    'first_name': 'الاسم الأول',
    'last_name': 'الاسم الأخير',
    'email': 'البريد الإلكتروني',

    # Inspection Fields
    'inspector': 'المفتش',
    'company': 'المنشأة المفتشة',
    'inspection_date': 'تاريخ التفتيش',
    'workers_size_estimation': 'تقدير حجم العمالة',
    'license_compliance': 'مطابقة الرخصة للموقع',
    'female_workers_element': 'العنصر النسائي',
    'unlicensed_workers': 'عمال دون ترخيص',
    'penalties_regulation': 'لائحة الجزاءات',
    'work_regulation': 'لائحة تنظيم العمل',
    'worker_file_maintenance': 'الاحتفاظ بملف العامل',
    'extended_working_hours': 'ساعات العمل الإضافية',
    'consecutive_shifts': 'الورديات المتتالية',
    'weekly_rest_schedule': 'جدول الراحة الأسبوعية',
    'number_of_shifts': 'عدد ورديات العمل',
    'inspector_opinion': 'رأي المفتش',
    'mandoub_name_1': 'اسم المندوب الأول',
    'mandoub_phone_1': 'جوال المندوب الأول',
    'mandoub_name_2': 'اسم المندوب الثاني',
    'mandoub_phone_2': 'جوال المندوب الثاني',
    'inspection_status': 'حالة التقرير',
    
    # the generic field for any model's ID (primary key)
    'id': 'الرقم التعريفي (ID)',
}

@register.filter
def prettify_log(changes_json, key_type):
    """
    يقوم بمعالجة نص سجل التدقيق (سواء كان اسم الحقل أو القيمة)
    لتحسين القراءة وإزالة التداخل اللغوي.
    """
    
    # 1. processing field names (key_type='field')
    if key_type == 'field':
        return FIELD_NAMES.get(changes_json, changes_json)

    # 2. processing values (key_type='value')
    # 2. processing values (key_type='value')
    if key_type == 'value':
        # if the value is None or empty, return a default Arabic string
        if changes_json is None or str(changes_json).lower() == 'none' or changes_json == '':
            return 'فارغ' 
        
        # convert the value to string and lower case for comparison
        val_str = str(changes_json).strip().lower()
        
        
        VALUE_TRANSLATIONS = {
            'true': 'نشط / مفعل',
            'false': 'غير نشط',
            'active': 'نشط',
            'deleted': 'محذوف',
        }
        
        # check if the value is in the translations dictionary
        if val_str in VALUE_TRANSLATIONS:
            return VALUE_TRANSLATIONS[val_str]
        
        # if the value is a digit, return it as an ID representation
        if str(changes_json).isdigit():
            return f"(ID: {changes_json})"

        return changes_json

    return changes_json