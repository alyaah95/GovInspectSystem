from django.db import models
from django.contrib.auth.models import AbstractUser
from django.contrib.auth import get_user_model
from django.conf import settings
from auditlog.registry import auditlog
from cloudinary_storage.storage import MediaCloudinaryStorage
# choices for company type, inspector status, compliance, gender, violation, regulations, shift, and inspection status
COMPANY_TYPE_CHOICES = [
    ('commercial_shop', 'محل تجاري'),
    ('commercial_building', 'عقار تجاري'),
    ('factory', 'مصنع'),
    ('lab', 'معمل'),
    ('apartment', 'شقة'),
    ('workshop', 'ورشة'),
    ('office', 'مكتب'),
    ('villa', 'فيلا'),
    ('other', 'اخرى'),
]

INSPECTOR_STATUS_CHOICES = [
    ('not_assigned', ('لم يتم التعيين')),
    ('assigned', ('تم التعيين')),
    ('accepted', ('تم القبول')),
    ('declined', ('تم الرفض')),
    ('in_progress', ('قيد العمل')),
    ('completed', ('مكتملة'))
]

COMPLIANCE_CHOICES = [
    ('compliant', 'مطابقة'),
    ('non_compliant', 'غير مطابقة'),
    ('unspecified', 'غير محدد'),
]

GENDER_CHOICES = [
    ('feasible', 'قابل'),
    ('not_feasible', 'غير قابل'),
    ('unspecified', 'غير محدد'),
]

VIOLATION_CHOICES = [
    ('non_violation', 'غير مخالف'),
    ('violation', 'مخالف'),
    ('unspecified', 'غير محدد'),
]

REGULATIONS_CHOICES = [
    ('exists', 'يوجد'),
    ('not_exists', 'لا يوجد'),
    ('not_applicable', 'لا ينطبق'),
]

SHIFT_CHOICES = [
    ('one_shift', 'وردية واحدة'),
    ('two_shifts', 'ورديتان'),
    ('three_shifts', 'ثلاثة ورديات'),
]

INSPECTION_STATUS_CHOICES = (
    ('draft', 'مسودة'),
    ('pending_approval', 'بانتظار الموافقة'),
    ('approved', 'موافق عليه'),
    ('rejected', 'مرفوض'),
    ('archived', 'مؤرشف'), 
    ('deleted', 'محذوف'),    
)

class User(AbstractUser):
    phone_number = models.CharField(max_length=20, verbose_name='رقم الجوال', unique=True)
    address = models.CharField(max_length=255, verbose_name='العنوان')
    user_id = models.CharField(max_length=100, verbose_name='رقم الهوية', unique=True)
    supervisor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='supervised_inspectors' # the reverse relation name for supervisors to access their inspectors
    )
    date_joined = models.DateTimeField(auto_now_add=True, verbose_name='تاريخ الانضمام', db_index=True)


    def __str__(self):
        return self.username
    
# company model to store the basic information about the company, its location, and its status. The manager can assign an inspector to the company, and the inspector can fill in the inspection details later.
class Company(models.Model):
    company_name = models.CharField(max_length=255, verbose_name='اسم المنشأة', db_index=True)
    company_number = models.CharField(max_length=100, verbose_name='رقم المنشأة')
    region = models.CharField(max_length=100, verbose_name='اسم المنطقة',  db_index=True)
    street_name = models.CharField(max_length=255, verbose_name='اسم الشارع')
    building_number = models.CharField(max_length=50, verbose_name='رقم العقار')
    activity_type = models.CharField(max_length=100, verbose_name='نوع النشاط')
    electricity_meter_number = models.CharField(max_length=50, verbose_name='رقم الكهرباء')
    actual_workers_count = models.IntegerField(default=0, verbose_name='عدد العمال الفعلي')
    establishment_type = models.CharField(max_length=50, choices=COMPANY_TYPE_CHOICES, verbose_name='المنشأة عبارة عن')
    size_description = models.TextField(verbose_name='حجم المنشأة والمساحة التقريبية بالوصف')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاريخ إضافة الشركة',  db_index=True) # حقل جديد
    # is_deleted = models.BooleanField(default=False, verbose_name='تم الحذف')
    status = models.CharField(max_length=50, default='active', verbose_name='الحالة')  # حالات: active, archived, deleted
    manager = models.ForeignKey(
        get_user_model(),
        on_delete=models.SET_NULL,
        related_name='companies_managed',
        null=True,
        verbose_name='المدير المسؤول'
    )
    # the inspector assigned to the company, and the status of the assignment (not assigned, assigned, accepted, declined, in progress, completed)
    assigned_to = models.ForeignKey(
        get_user_model(),
        on_delete=models.SET_NULL,
        related_name='companies_inspected',
        null=True,
        blank=True,
        verbose_name='المفتش المعين'
    )
    status_by_inspector = models.CharField(
        max_length=20,
        choices=INSPECTOR_STATUS_CHOICES,
        default='not_assigned',
        verbose_name='حالة التعيين'
    )
    decline_reason = models.TextField(
        ("سبب الرفض"), 
        blank=True, 
        null=True
    )

    class Meta:
        verbose_name = 'منشأة'
        verbose_name_plural = 'منشآت'
        indexes = [
            models.Index(fields=['company_name', 'region']),
        ]

    def __str__(self):
        return self.company_name
    
    

# a model to store images related to a company, with a foreign key to the company and an image field for the image file. The description field is optional, and the uploaded_at field stores the date and time when the image was uploaded.
class CompanyImage(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, verbose_name='اسم المنشأة')
    image = models.ImageField(upload_to='company_images/',storage=MediaCloudinaryStorage(), verbose_name='الصورة')
    description = models.CharField(max_length=255, blank=True, verbose_name='وصف الصورة')
    uploaded_at = models.DateTimeField(auto_now_add=True, verbose_name='تاريخ الرفع')

    def __str__(self):
        return f"Image for {self.company}"

# a model to store notifications for users, with a foreign key to the recipient user and an optional foreign key to the sender user. The title and message fields store the notification content, and the related_company field links the notification to a specific company if applicable. The is_read field indicates whether the notification has been read, and the created_at field stores the date and time when the notification was created.
class Notification(models.Model):
    recipient = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='notifications',
        verbose_name=("المستلم")
    )
    sender = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='sent_notifications',
        verbose_name=("المرسل")
    )
    title = models.CharField(("العنوان"), max_length=255)
    message = models.TextField(("الرسالة"))
    related_company = models.ForeignKey(
        'Company',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name=("الشركة المتعلقة")
    )
    is_read = models.BooleanField(("تمت القراءة"), default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = ("إشعار")
        verbose_name_plural = ("إشعارات")
        ordering = ['-created_at']

    def __str__(self):
        return self.title
    
# a model to store inspection reports, with a foreign key to the inspector user and a foreign key to the company being inspected. The inspection_date field stores the date and time of the inspection, and various fields store the inspector's findings and opinions. The status field indicates the current status of the inspection report (draft, pending approval, approved, rejected, archived, deleted), and the updated_at field stores the date and time when the report was last updated.
class Inspection(models.Model):
    inspector = models.ForeignKey(get_user_model(), on_delete=models.PROTECT, verbose_name='المفتش')
    company = models.ForeignKey(Company, on_delete=models.CASCADE, verbose_name='اسم المنشأة')
    inspection_date = models.DateTimeField(auto_now_add=True, verbose_name='تاريخ التفتيش', db_index=True)
    workers_size_estimation = models.CharField(max_length=255, verbose_name='تقدير المفتش لحجم العمالة')
    license_compliance = models.CharField(max_length=50, choices=COMPLIANCE_CHOICES, verbose_name='مطابقة الرخصة للموقع')
    female_workers_element = models.CharField(max_length=50, choices=GENDER_CHOICES, verbose_name='العنصر النسائي')
    unlicensed_workers = models.CharField(max_length=50, choices=VIOLATION_CHOICES, verbose_name='استخدام عمال دون ترخيص')
    penalties_regulation = models.CharField(max_length=50, choices=REGULATIONS_CHOICES, verbose_name='لائحة الجزاءات')
    work_regulation = models.CharField(max_length=50, choices=REGULATIONS_CHOICES, verbose_name='لائحة تنظيم العمل')
    worker_file_maintenance = models.CharField(max_length=50, choices=VIOLATION_CHOICES, verbose_name='الاحتفاظ بملف خاص لكل عامل')
    extended_working_hours = models.CharField(max_length=50, choices=VIOLATION_CHOICES, verbose_name='تشغيل العامل أكثر من الساعات المحددة')
    consecutive_shifts = models.CharField(max_length=50, choices=VIOLATION_CHOICES, verbose_name='تشغيل العامل أكثر من جمعتين متتاليتين')
    weekly_rest_schedule = models.CharField(max_length=50, choices=VIOLATION_CHOICES, verbose_name='جدول ساعات العمل والراحة الأسبوعية')
    number_of_shifts = models.CharField(max_length=50, choices=SHIFT_CHOICES, verbose_name='عدد ورديات العمل')
    inspector_opinion = models.TextField(verbose_name='رأي المفتش')
    mandoub_name_1 = models.CharField(max_length=100,blank=True, verbose_name='اسم المندوب (1)')
    mandoub_phone_1 = models.CharField(max_length=20,blank=True, verbose_name='رقم الجوال (1)')
    mandoub_name_2 = models.CharField(max_length=100, blank=True, verbose_name='اسم المندوب (2)')
    mandoub_phone_2 = models.CharField(max_length=20, blank=True, verbose_name='رقم الجوال (2)')
    status = models.CharField(max_length=50, default='draft',choices=INSPECTION_STATUS_CHOICES, verbose_name='الحالة')  # draft, pending approval, approved, rejected, archived, deleted
    updated_at = models.DateTimeField(auto_now=True, verbose_name='تاريخ التحديث')

    class Meta:
        indexes = [
            models.Index(fields=['inspector', 'inspection_date']),
        ]

    def __str__(self):
        return f"Inspection on {self.company.company_name} - {self.inspection_date.date()}"

# a model to store images related to an inspection report, with a foreign key to the inspection and an image field for the image file. The description field is optional, and the uploaded_at field stores the date and time when the image was uploaded.
class InspectionImage(models.Model):
    inspection = models.ForeignKey(Inspection, on_delete=models.CASCADE, verbose_name='تقرير التفتيش')
    image = models.ImageField(upload_to='inspection_images/',storage=MediaCloudinaryStorage(), verbose_name='الصورة')
    description = models.CharField(max_length=255, blank=True, verbose_name='وصف الصورة')
    uploaded_at = models.DateTimeField(auto_now_add=True, verbose_name='تاريخ الرفع')

    def __str__(self):
        return f"Image for {self.inspection}"
    

auditlog.register(User)
auditlog.register(Company)
auditlog.register(Inspection)