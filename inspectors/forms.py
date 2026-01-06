from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import get_user_model, authenticate
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.contrib.auth.forms import SetPasswordForm
from django.forms import formset_factory, inlineformset_factory
from .models import Company, Inspection, InspectionImage, CompanyImage, Notification
from django.contrib.auth.forms import UserCreationForm
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth.models import Group
from django.contrib.sites.shortcuts import get_current_site
from django.template.loader import render_to_string
from django.core.mail import EmailMessage
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.contrib.auth.tokens import default_token_generator


User = get_user_model()



class InspectorAuthenticationForm(AuthenticationForm):
    def __init__(self, request=None, *args, **kwargs):
        super().__init__(request=request, *args, **kwargs)
        self.fields['username'].label = 'البريد الإلكتروني أو اسم المستخدم'
        self.fields['password'].label = 'كلمة المرور'
        self.fields['username'].widget.attrs['placeholder'] = 'البريد الإلكتروني أو اسم المستخدم'

    def clean(self):
        username = self.cleaned_data.get('username')
        password = self.cleaned_data.get('password')

        if username and password:
            self.user_cache = authenticate(self.request, username=username, password=password)
            if self.user_cache is None:
                raise self.get_invalid_login_error()
            else:
                self.confirm_login_allowed(self.user_cache)
        return self.cleaned_data


class InspectorSetPasswordForm(forms.Form):
    new_password1 = forms.CharField(
        label='كلمة المرور الجديدة',
        widget=forms.PasswordInput,
        help_text='يجب أن تحتوي على 8 أحرف على الأقل، وألا تكون شائعة الاستخدام أو أرقامًا فقط.'
    )
    new_password2 = forms.CharField(
        label='تأكيد كلمة المرور الجديدة',
        widget=forms.PasswordInput,
    )

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean(self):
        super().clean()
        password = self.cleaned_data.get('new_password1')
        password2 = self.cleaned_data.get('new_password2')

        if password and password2 and password != password2:
            raise forms.ValidationError('كلمتا المرور غير متطابقتين.')

        if password:
            try:
                validate_password(password, self.user)
            except ValidationError as error:
                translated_errors = []
                for msg in error.messages:
                    if "too short" in msg:
                        translated_errors.append('كلمة المرور قصيرة جداً. يجب أن تحتوي على 8 أحرف على الأقل.')
                    elif "too common" in msg:
                        translated_errors.append('كلمة المرور هذه شائعة الاستخدام.')
                    elif "entirely numeric" in msg:
                        translated_errors.append('كلمة المرور هذه تتكون من أرقام فقط.')
                    elif "too similar" in msg:
                        translated_errors.append('لا يمكن أن تكون كلمة المرور مشابهة لمعلوماتك الشخصية الأخرى.')
                    elif "cannot contain the email address" in msg:
                        translated_errors.append('لا يمكن أن تحتوي كلمة المرور على عنوان البريد الإلكتروني.')
                    elif "cannot contain the username" in msg:
                        translated_errors.append('لا يمكن أن تحتوي كلمة المرور على اسم المستخدم.')
                    else:
                        translated_errors.append(msg)
                
                raise forms.ValidationError(translated_errors)
        return self.cleaned_data

    def save(self, commit=True):
        password = self.cleaned_data["new_password1"]
        self.user.set_password(password)
        if commit:
            self.user.save()
        return self.user


class InspectorCreationForm(UserCreationForm):
    username = forms.CharField(label='اسم المستخدم', max_length=245, error_messages={
            'required': 'هذا الحقل مطلوب.',
            'unique': '  اسم المستخدم هذا مُستخدم بالفعل.',
        })
    first_name = forms.CharField(label='الاسم الأول', max_length=30, error_messages={
        'required': 'هذا الحقل مطلوب.',
    })
    last_name = forms.CharField(label='اسم العائلة', max_length=30, error_messages={
        'required': 'هذا الحقل مطلوب.',
    })
    email = forms.EmailField(
        label='البريد الإلكتروني',
        max_length=254,
        error_messages={
            'required': 'هذا الحقل مطلوب.',
            'unique': 'هذا البريد الإلكتروني مُستخدم بالفعل.',
        }
    )
    phone_number = forms.CharField(
        label='رقم الجوال',
        max_length=15,
        error_messages={
            'required': 'هذا الحقل مطلوب.',
            'unique': 'رقم الجوال مُستخدم بالفعل.',
        }
    )
    user_id = forms.CharField(
        label='رقم الهوية',
        max_length=20,
        error_messages={
            'required': 'هذا الحقل مطلوب.',
            'unique': 'رقم الهوية مُستخدم بالفعل.',
        }
    )
    address = forms.CharField(
        label='عنوان السكن',
        max_length=200,
        error_messages={
            'required': 'هذا الحقل مطلوب.',
        }
    )
    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('username','first_name','last_name','email','phone_number', 'user_id', 'address')
    
    def clean_username(self):
        username = self.cleaned_data.get('username')
        if User.objects.filter(username=username).exists():
            # استخدام forms.ValidationError لرفع رسالة الخطأ المخصصة
            raise forms.ValidationError('اسم المستخدم مُستخدم بالفعل.')
        return username

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError('هذا البريد الإلكتروني مُستخدم بالفعل.')
        return email

    def clean_phone_number(self):
        phone_number = self.cleaned_data.get('phone_number')
        if User.objects.filter(phone_number=phone_number).exists():
            raise forms.ValidationError('رقم الجوال مُستخدم بالفعل.')
        return phone_number

    def clean_user_id(self):
        user_id = self.cleaned_data.get('user_id')
        if User.objects.filter(user_id=user_id).exists():
            raise forms.ValidationError('رقم الهوية مُستخدم بالفعل.')
        return user_id
    

    def save(self, request=None, supervisor=None, commit=True):
        user = super().save(commit=False)
        user.is_active = True

        if supervisor:
            user.supervisor = supervisor
        
        # حفظ المستخدم وتعيين المجموعة
        if commit:
            user.save()
            group, created = Group.objects.get_or_create(name='Inspectors')
            user.groups.add(group)
            
            # **الكود الجديد لإرسال رابط إعادة تعيين كلمة المرور**
            current_site = get_current_site(request)
            subject = 'تفعيل حسابك في GovInspectSystem'
            
            message = render_to_string('inspectors/activation_email.html', {
                'user': user,
                'domain': current_site.domain,
                'uid': urlsafe_base64_encode(force_bytes(user.pk)),
                'token': default_token_generator.make_token(user),
            })
            
            email = EmailMessage(subject, message, to=[user.email])
            email.send()
            
        return user

class CustomUserCreationForm(forms.ModelForm):
    # لا نقوم بتعريف حقول كلمة المرور هنا.
    
    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email', 'phone_number', 'user_id', 'address')
        labels = {
            'username': ('اسم المستخدم'),
            'first_name': ('الاسم الأول'),
            'last_name': ('اسم العائلة'),
            'email': ('البريد الإلكتروني'),
            'phone_number': ('رقم الجوال'),
            'user_id': ('رقم الهوية'),
            'address': ('العنوان'),
        }

    # بما أننا لا نستخدم حقول كلمة المرور، فإننا لا نحتاج إلى إضافة دالة clean.
    # ببساطة نترك النموذج يقوم بالتحقق الافتراضي.

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_unusable_password()
        if commit:
            user.save()
        return user
    
class UserProfileEditForm(forms.ModelForm):
    # *ملاحظة:* لا ندرج حقل 'username' في التعديل عادةً لتجنب المشاكل،
    # ولا ندرج حقول كلمة المرور.
    first_name = forms.CharField(label='الاسم الأول', max_length=30, error_messages={
        'required': 'هذا الحقل مطلوب.',
    })
    last_name = forms.CharField(label='اسم العائلة', max_length=30, error_messages={
        'required': 'هذا الحقل مطلوب.',
    })
    email = forms.EmailField(
        label='البريد الإلكتروني',
        max_length=254,
        error_messages={
            'required': 'هذا الحقل مطلوب.',
            'unique': 'هذا البريد الإلكتروني مُستخدم بالفعل.',
        }
    )
    phone_number = forms.CharField(
        label='رقم الجوال',
        max_length=15,
        error_messages={
            'required': 'هذا الحقل مطلوب.',
            'unique': 'رقم الجوال مُستخدم بالفعل.',
        }
    )
    user_id = forms.CharField(
        label='رقم الهوية',
        max_length=20,
        error_messages={
            'required': 'هذا الحقل مطلوب.',
            'unique': 'رقم الهوية مُستخدم بالفعل.',
        }
    )
    address = forms.CharField(
        label='عنوان السكن',
        max_length=200,
        error_messages={
            'required': 'هذا الحقل مطلوب.',
        }
    )

    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'email', 'phone_number', 'user_id', 'address')
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.exclude(pk=self.instance.pk).filter(email=email).exists():
            raise forms.ValidationError('هذا البريد الإلكتروني مُستخدم بالفعل.')
        return email

    def clean_phone_number(self):
        phone_number = self.cleaned_data.get('phone_number')
        if User.objects.exclude(pk=self.instance.pk).filter(phone_number=phone_number).exists():
            raise forms.ValidationError('رقم الجوال مُستخدم بالفعل.')
        return phone_number

    def clean_user_id(self):
        user_id = self.cleaned_data.get('user_id')
        if User.objects.exclude(pk=self.instance.pk).filter(user_id=user_id).exists():
            raise forms.ValidationError('رقم الهوية مُستخدم بالفعل.')
        return user_id
     
    



# قائمة المستخدمين المفتشين
# INSPECTOR_CHOICES = [(user.id, user.username) for user in User.objects.filter(groups__name='Inspectors')]

class ManagerCompanyForm(forms.ModelForm):
    # المدير هو من يضيف البيانات الأولية
    assigned_to = forms.ModelChoiceField(
        queryset=User.objects.filter(groups__name='Inspectors'),
        required=True,
        label='تعيين مفتش'
    )

    class Meta:
        model = Company
        fields = [
            'company_name', 'company_number', 'region', 'street_name', 'building_number',
            'assigned_to'
        ]
        labels = {
            'company_name': 'اسم المنشأة',
            'company_number': 'رقم المنشأة',
            'region': 'اسم المنطقة',
            'street_name': 'اسم الشارع',
            'building_number': 'رقم العقار',
            'assigned_to': 'تعيين مفتش',
        }

class InspectorCompanyForm(forms.ModelForm):
    # المفتش يكمل البيانات الميدانية
    class Meta:
        model = Company
        fields = [
            'company_name', 'company_number', 'region', 'street_name', 'building_number',
            'activity_type', 'electricity_meter_number', 'actual_workers_count',
            'establishment_type', 'size_description',
        ]
        labels = {
            'company_name': 'اسم المنشأة',
            'company_number': 'رقم المنشأة',
            'region': 'اسم المنطقة',
            'street_name': 'اسم الشارع',
            'building_number': 'رقم العقار',
            'activity_type': 'نوع النشاط',
            'electricity_meter_number': 'رقم الكهرباء',
            'actual_workers_count': 'عدد العمال الفعلي',
            'establishment_type': 'المنشأة عبارة عن',
            'size_description': 'حجم المنشأة والمساحة التقريبية بالوصف',
        }
        widgets = {
            'actual_workers_count': forms.NumberInput(attrs={'min': 0}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # جعل الحقول الأساسية للقراءة فقط
        for field in self.fields:
            if field in ['company_name', 'company_number', 'region', 'street_name', 'building_number']:
                self.fields[field].widget.attrs['readonly'] = True


# النموذج الجديد لإضافة سبب الرفض
class DeclineReasonForm(forms.Form):
    reason = forms.CharField(
        label="سبب الرفض",
        widget=forms.Textarea(attrs={'rows': 4}),
        required=True
    )


class CompanyImageForm(forms.ModelForm):
    # هذا النموذج خاص بحقول الصورة
    class Meta:
        model = CompanyImage
        fields = ['image', 'description']
        labels = {
            'image': 'الصورة',
            'description': 'وصف الصورة',
        }

# هذا هو الـ Formset الذي يربط بين الشركة وصورها
CompanyImageFormSet = inlineformset_factory(
    Company,
    CompanyImage,
    form=CompanyImageForm,
    extra=1,
    can_delete=True
)


class InspectionForm(forms.ModelForm):
    class Meta:
        model = Inspection
        fields = [
            'workers_size_estimation', 'license_compliance', 'female_workers_element',
            'unlicensed_workers', 'penalties_regulation', 'work_regulation',
            'worker_file_maintenance', 'extended_working_hours',
            'consecutive_shifts', 'weekly_rest_schedule', 'number_of_shifts',
            'inspector_opinion', 'mandoub_name_1', 'mandoub_phone_1',
            'mandoub_name_2', 'mandoub_phone_2'
        ]
        labels = {
            'workers_size_estimation': 'تقدير المفتش لحجم العمالة',
            'license_compliance': 'مطابقة الرخصة للموقع',
            'female_workers_element': 'العنصر النسائي',
            'unlicensed_workers': 'استخدام عمال دون ترخيص',
            'penalties_regulation': 'لائحة الجزاءات',
            'work_regulation': 'لائحة تنظيم العمل',
            'worker_file_maintenance': 'الاحتفاظ بملف خاص لكل عامل',
            'extended_working_hours': 'تشغيل العامل أكثر من الساعات المحددة',
            'consecutive_shifts': 'تشغيل العامل أكثر من جمعتين متتاليتين',
            'weekly_rest_schedule': 'جدول ساعات العمل والراحة الأسبوعية',
            'number_of_shifts': 'عدد ورديات العمل',
            'inspector_opinion': 'رأي المفتش',
            'mandoub_name_1': 'اسم المندوب (1)',
            'mandoub_phone_1': 'رقم الجوال (1)',
            'mandoub_name_2': 'اسم المندوب (2)',
            'mandoub_phone_2': 'رقم الجوال (2)',
        }
        error_messages = {
            'workers_size_estimation': {
                'required': 'تقدير المفتش لحجم العمالة مطلوب.'
            },
            'license_compliance': {
                'required': 'اختيار مطابقة الرخصة للموقع مطلوب.'
            },
            'female_workers_element': {
                'required': 'اختيار العنصر النسائي مطلوب.'
            },
            'unlicensed_workers': {
                'required': 'اختيار استخدام عمال دون ترخيص مطلوب.'
            },
            'penalties_regulation': {
                'required': 'اختيار لائحة الجزاءات مطلوب.'
            },
            'work_regulation': {
                'required': 'اختيار لائحة تنظيم العمل مطلوب.'
            },
            'worker_file_maintenance': {
                'required': 'اختيار الاحتفاظ بملف خاص لكل عامل مطلوب.'
            },
            'extended_working_hours': {
                'required': 'اختيار تشغيل العامل أكثر من الساعات المحددة مطلوب.'
            },
            'consecutive_shifts': {
                'required': 'اختيار تشغيل العامل أكثر من جمعتين متتاليتين مطلوب.'
            },
            'weekly_rest_schedule': {
                'required': 'اختيار جدول ساعات العمل والراحة الأسبوعية مطلوب.'
            },
            'number_of_shifts': {
                'required': 'اختيار عدد ورديات العمل مطلوب.'
            },
            'inspector_opinion': {
                'required': 'إدخال رأي المفتش مطلوب.'
            }
        }

# هذا هو الـ Formset الذي يربط التقرير بصوره
InspectionImageFormSet = inlineformset_factory(
    Inspection,
    InspectionImage,
    fields=('image', 'description'),
    extra=1,
    can_delete=True
)
