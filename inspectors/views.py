import os
from django.shortcuts import render, redirect, get_object_or_404
from .forms import InspectorCreationForm, CompanyImageForm, ManagerCompanyForm, InspectorCompanyForm, InspectionForm, InspectionImageFormSet, InspectorAuthenticationForm, DeclineReasonForm, UserProfileEditForm
from django.contrib.auth import login, logout
from django.forms import inlineformset_factory
from django.contrib.auth.forms import AuthenticationForm
from django.core.mail import send_mail
from django.conf import settings
from django.views.decorators.csrf import requires_csrf_token
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import Group
from .models import Company, Inspection, InspectionImage, CompanyImage, Notification
from django.contrib import messages
from django.core.mail import EmailMessage
from django.db import transaction
from django.db.models import Q
from django.utils.dateparse import parse_date
from django.utils import timezone
from django.template.loader import render_to_string
from django.http import HttpResponse
from xhtml2pdf import pisa
import io
from datetime import date
from auditlog.models import LogEntry
from django.contrib.contenttypes.models import ContentType


from django.contrib.auth import get_user_model
User = get_user_model()



def home(request):
    return render(request, 'inspectors/home.html')



def login_view(request):
    if request.method == 'POST':
        form = InspectorAuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect('home')
    else:
        form = InspectorAuthenticationForm()
    return render(request, 'inspectors/login.html', {'form': form})


@requires_csrf_token
def csrf_failure(request, reason=''):
    context = {'reason': reason}
    return render(request, 'inspectors/csrf_failure.html', context)


def logout_view(request):
    logout(request)
    return redirect('login')

def is_manager(user):
    return user.is_authenticated and user.groups.filter(name='Managers').exists()

def is_inspector(user):
    return user.is_authenticated and user.groups.filter(name='Inspectors').exists()

# دالة لإرسال إشعار بالبريد الإلكتروني
def send_assignment_notification(company):
    inspector = company.assigned_to
    if inspector and inspector.email:
        subject = f"تم تعيين منشأة جديدة لك: {company.company_name}"
        message = f"مرحباً {inspector.username},\n\nتم تعيين منشأة جديدة لك لإجراء التفتيش عليها:\n{company.company_name} - {company.region}\n\nيرجى تسجيل الدخول إلى النظام لتأكيد الاستلام والبدء في العمل."
        email = EmailMessage(
            subject,
            message,
            to=[inspector.email]
        )
        email.send()

# دالة مساعدة لإنشاء إشعار
def create_notification(recipient, sender, title, message, company=None):
    Notification.objects.create(
        recipient=recipient,
        sender=sender,
        title=title,
        message=message,
        related_company=company
    )

@user_passes_test(is_manager)
def add_inspector_view(request):
    if request.method == 'POST':
        form = InspectorCreationForm(request.POST)
        if form.is_valid():
            user = form.save(request=request, supervisor=request.user)
            messages.success(request, f'تم إضافة المفتش {user.username} بنجاح.')
            return redirect('add_inspector')
    else:
        form = InspectorCreationForm()
    return render(request, 'inspectors/add_inspector.html', {'form': form})


# دالة عرض الملف الشخصي
@login_required(login_url='login')
def profile_detail_view(request):
    # لا تحتاجين لاسترجاع بيانات إضافية طالما كل شيء في نموذج User
    # لكن يمكنك إضافة معلومات إحصائية إذا كانت متوفرة
    
    context = {
        'user': request.user,
    }
    return render(request, 'profiles/profile_detail.html', context)


from django.db.models import Q # لاستخدام OR في البحث

@login_required(login_url='login')
@user_passes_test(is_manager)
def inspectors_list_view(request):
    # 1. الاستعلام الأساسي: جلب المفتشين التابعين للمدير
    inspectors = User.objects.filter(
        groups__name='Inspectors',
        supervisor=request.user
    )

    # 2. تطبيق البحث (Searching)
    search_query = request.GET.get('q') # الحصول على قيمة خانة البحث
    if search_query:
        # البحث في حقول متعددة باستخدام Q (OR logic)
        inspectors = inspectors.filter(
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(username__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(user_id__icontains=search_query) 
        )

    # 3. تطبيق التصفية (Filtering) حسب حالة النشاط (is_active)
    filter_status = request.GET.get('status') # الحصول على قيمة التصفية
    if filter_status:
        if filter_status == 'active':
            inspectors = inspectors.filter(is_active=True)
        elif filter_status == 'inactive':
            inspectors = inspectors.filter(is_active=False)
    
    # 4. تطبيق الترتيب (Ordering)
    
    # الافتراضي يكون حسب الاسم الأخير ثم الاسم الأول
    default_order = 'last_name' 
    order_by = request.GET.get('order_by', default_order)

    # قائمة الحقول الآمنة للترتيب
    # نستخدم حقول الاسم، اسم المستخدم، تاريخ الانضمام، وحالة النشاط
    allowed_orders = ['last_name', '-last_name', 'username', '-username', 'date_joined', '-date_joined', '-is_active', 'is_active'] 
    
    if order_by in allowed_orders:
        inspectors = inspectors.order_by(order_by)
    else:
        # إذا كانت القيمة غير آمنة، نستخدم الترتيب الافتراضي
        inspectors = inspectors.order_by(default_order)

    if not inspectors.exists():
        messages.info(request, "لا يوجد مفتشون مطابقون لمعايير البحث/التصفية.")
    
    context = {
        'inspectors': inspectors,
        'page_title': 'المفتشون التابعون لي',
        'search_query': search_query, # تمرير قيمة البحث للحفاظ عليها في النموذج
        'filter_status': filter_status, # تمرير قيمة التصفية للحفاظ عليها
        'current_order': order_by,
    }
    return render(request, 'inspectors/inspectors_list.html', context)

@login_required(login_url='login')
@user_passes_test(is_manager)
def inspector_detail_view(request, pk):
    
    # 2. جلب بيانات المفتش
    inspector = get_object_or_404(User, pk=pk)

    # 3. التأكد من أن المستخدم المُستعرض هو مفتش فعلاً (للتأمين)
    if inspector.supervisor != request.user or inspector.is_superuser or not inspector.groups.filter(name='Inspectors').exists():
        messages.error(request, "المستخدم المطلوب ليس مفتشاً.")
        return redirect('inspectors_list')
        
    # يمكن هنا إضافة معلومات إحصائية للمفتش (مثل عدد التقارير)
    
    context = {
        'inspector': inspector,
        'page_title': f'تفاصيل المفتش: {inspector.get_full_name()}',
    }
    return render(request, 'inspectors/inspector_detail.html', context)


# دالة تعديل الملف الشخصي
@login_required(login_url='login')
def edit_profile_view(request):
    if request.method == 'POST':
        # نستخدم instance=request.user لملء النموذج ببيانات المستخدم الحالي
        form = UserProfileEditForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'تم تحديث ملفك الشخصي بنجاح. ✅')
            return redirect('user_profile') # يفترض أن اسم الـ url هو 'user_profile'
        else:
            # رسائل خطأ حقول النموذج ستظهر تلقائياً
            messages.error(request, 'الرجاء تصحيح الأخطاء في النموذج. ❌')
    else:
        form = UserProfileEditForm(instance=request.user)

    context = {
        'form': form,
        'page_title': 'تعديل الملف الشخصي',
        'user': request.user, # لتتمكني من عرض اسم المستخدم/البريد في القالب
    }
    return render(request, 'profiles/edit_profile.html', context)


@login_required(login_url='login')
@user_passes_test(is_manager) 
def manager_edit_inspector_view(request, pk):
    """
    تسمح للمدير بتعديل بيانات مفتش محدد (باستخدام الـ pk).
    """
    # 1. جلب كائن المفتش
    inspector = get_object_or_404(User, pk=pk)
    
    # 2. تحقق أمان إضافي: التأكد من أن الكائن هو مفتش (أو ليس المدير نفسه إذا أردتِ)
    if inspector.supervisor != request.user or inspector.is_superuser or not inspector.groups.filter(name='Inspectors').exists():
        messages.error(request, 'ليس لديك الصلاحية لتعديل بيانات هذا المستخدم، إما لأنه ليس تابعًا لك أو ليس مفتشًا معتمدًا.')
        return redirect('inspectors_list')

    if request.method == 'POST':
        # 3. ربط النموذج ببيانات الـ POST وكائن المفتش (instance=inspector)
        form = UserProfileEditForm(request.POST, instance=inspector)
        if form.is_valid():
            form.save()
            messages.success(request, f'تم تعديل بيانات المفتش {inspector.username} بنجاح. ✅')
            return redirect('inspectors_list') 
        else:
            messages.error(request, 'الرجاء تصحيح الأخطاء في النموذج. ❌')
    else:
        # 4. عرض النموذج لأول مرة مع ملئه ببيانات المفتش
        form = UserProfileEditForm(instance=inspector)

    context = {
        'form': form,
        'page_title': f'تعديل المفتش: {inspector.username}',
        'user_to_edit': inspector, 
    }
    # يجب التأكد من وجود القالب 'inspectors/inspector_edit.html'
    return render(request, 'inspectors/inspector_edit.html', context)

@login_required(login_url='login')
def companies_list(request):
    query = request.GET.get('q', '').strip()
    start_date = request.GET.get('start_date', '').strip()
    end_date = request.GET.get('end_date', '').strip()
    sort_order = request.GET.get('sort_order', '-created_at') # الترتيب الافتراضي

    if is_manager(request.user):
        companies = Company.objects.filter(status='active').order_by('-created_at')
    # المفتش يرى المنشآت المعينة له فقط
    elif is_inspector(request.user):
        companies = Company.objects.filter(assigned_to=request.user, status='active').order_by('-created_at')
    else:
        companies = Company.objects.none()

    unread_notifications_count = Notification.objects.filter(recipient=request.user, is_read=False).count()

    # فلترة بالبحث النصي
    if query:
        companies = companies.filter(
            Q(company_name__icontains=query) | Q(region__icontains=query)
        )

    # فلترة بالتاريخ لو المستخدم اختار تاريخ
    if start_date and end_date:
        start = parse_date(start_date)
        end = parse_date(end_date)
        if start and end:
            companies = companies.filter(created_at__date__range=(start, end))

    # تطبيق الترتيب حسب الطلب
    companies = companies.order_by(sort_order)

    context = {
        'companies': companies,
        'query': query,
        'start_date': start_date,
        'end_date': end_date,
        'sort_order': sort_order, # تمرير قيمة الترتيب إلى القالب
        'unread_notifications_count': unread_notifications_count,
    }
    return render(request, 'inspectors/companies_list.html', context)



# 4. حذف ناعم (للمدير فقط)
@login_required(login_url='login')
@user_passes_test(is_manager)
def hide_company_view(request, pk):
    company = get_object_or_404(Company, pk=pk)
    company.status = 'deleted'
    company.save()
    messages.success(request, f"تم إخفاء منشأة {company.company_name} بنجاح.")
    return redirect('companies_list')


# 5. قائمة المنشآت المخفية (للمدير فقط)
@login_required(login_url='login')
@user_passes_test(is_manager)
def hidden_companies_list(request):
    query = request.GET.get('q', '').strip()
    start_date = request.GET.get('start_date', '').strip()
    end_date = request.GET.get('end_date', '').strip()
    sort_order = request.GET.get('sort_order', '-created_at')

    companies = Company.objects.filter(status='deleted')

    if query:
        companies = companies.filter(
            Q(company_name__icontains=query) | Q(region__icontains=query)
        )

    if start_date and end_date:
        start = parse_date(start_date)
        end = parse_date(end_date)
        if start and end:
            companies = companies.filter(created_at__date__range=(start, end))

    companies = companies.order_by(sort_order)

    context = {
        'companies': companies,
        'query': query,
        'start_date': start_date,
        'end_date': end_date,
        'sort_order': sort_order,
    }
    return render(request, 'inspectors/hidden_companies_list.html', context)


# 6. استعادة المنشأة المخفية (للمدير فقط)
@login_required(login_url='login')
@user_passes_test(is_manager)
def show_company_view(request, pk):
    company = get_object_or_404(Company, pk=pk)
    company.status = 'active'
    company.save()
    messages.success(request, f"تم استعادة منشأة {company.company_name} بنجاح.")
    return redirect('hidden_companies_list')



# 2. إضافة منشأة جديدة (للمدير فقط)
@login_required(login_url='login')
@user_passes_test(is_manager)
def add_company_view(request):
    if request.method == 'POST':
        form = ManagerCompanyForm(request.POST)
        if form.is_valid():
            company = form.save(commit=False)
            company.manager = request.user
            if company.assigned_to: 
                company.status_by_inspector = 'assigned' 
            company.save()
            # إنشاء إشعار داخل النظام
            create_notification(
                recipient=company.assigned_to,
                sender=request.user,
                title="تم تعيين منشأة جديدة لك",
                message=f"قام المدير {request.user.username} بتعيين منشأة {company.company_name} لك. يرجى تأكيد الاستلام.",
                company=company
            )
            send_assignment_notification(company) # إرسال إشعار
            messages.success(request, f"تم إضافة منشأة {company.company_name} بنجاح وتم تعيينها للمفتش.")
            return redirect('companies_list')
    else:
        form = ManagerCompanyForm()
    
    context = {'form': form}
    return render(request, 'inspectors/add_company.html', context)


# 3. قبول المهمة
@login_required(login_url='login')
@user_passes_test(is_inspector)
def accept_assignment_view(request, pk):
    company = get_object_or_404(Company, pk=pk, assigned_to=request.user)
    company.status_by_inspector = 'accepted'
    company.save()

    # إنشاء إشعار للمدير
    create_notification(
        recipient=company.manager,
        sender=request.user,
        title="تم قبول مهمة",
        message=f"المفتش {request.user.username} قام بقبول مهمة {company.company_name}.",
        company=company
    )

    messages.success(request, f"تم قبول مهمة {company.company_name} بنجاح.")
    return redirect('companies_list')

# 4. رفض المهمة
@login_required(login_url='login')
@user_passes_test(is_inspector)
def decline_assignment_view(request, pk):
    company = get_object_or_404(Company, pk=pk, assigned_to=request.user)

    if request.method == 'POST':
        form = DeclineReasonForm(request.POST)
        if form.is_valid():
            company.status_by_inspector = 'declined'
            company.decline_reason = form.cleaned_data['reason']
            company.assigned_to = None 
            company.status_by_inspector = 'declined' 
            company.save()
            
            # إنشاء إشعار للمدير مع سبب الرفض
            create_notification(
                recipient=company.manager,
                sender=request.user,
                title="تم رفض مهمة",
                message=f"المفتش {request.user.username} قام برفض مهمة {company.company_name}. سبب الرفض: {company.decline_reason}",
                company=company
            )
            
            messages.warning(request, f"تم رفض مهمة {company.company_name}.")
            return redirect('companies_list')
    else:
        form = DeclineReasonForm()
        
    context = {'company': company, 'form': form}
    return render(request, 'inspectors/decline_reason.html', context)


# 5. عرض الإشعارات
@login_required(login_url='login')
def notifications_view(request):
    notifications = Notification.objects.filter(recipient=request.user).order_by('-created_at')
    
    # وضع علامة "تمت القراءة" على جميع الإشعارات
    notifications.update(is_read=True)

    return render(request, 'inspectors/notifications.html', {'notifications': notifications})

@login_required(login_url='login')
def company_details_view(request, pk):
    company = get_object_or_404(Company, id=pk) # ✅ جلب الشركة أولاً
    if is_manager(request.user):
        pass # المدير لديه حق الوصول دائمًا
        
    elif is_inspector(request.user):
        # السماح للمفتش بالوصول إذا كان هو المعين حاليًا
        if company.assigned_to == request.user:
            pass
        else:
            # ✅ إضافة هذا الشرط للسماح للمفتشين غير المعينين بالوصول
            # يمكنكِ هنا جلب الشركة بدون فلترة assigned_to ثم التحقق يدويًا
            messages.error(request, "لم تعد هذه المنشأة مُعيّنة لك.")
            return redirect('companies_list') 
            
    else:
        return redirect('home')
    
    inspections = Inspection.objects.filter(company=company).exclude(status='deleted').order_by('-inspection_date')
    context = {
        'company': company,
        'inspections': inspections
    }
    return render(request, 'inspectors/company_details.html', context)



@login_required(login_url='login')
def edit_company_view(request, pk):
    # جلب الشركة من قاعدة البيانات
    company = get_object_or_404(Company, pk=pk)
    
    # حفظ القيمة الأصلية لـ assigned_to فوراً بعد جلب الشركة
    original_assigned_to = company.assigned_to
    
    # 1. تحديد مسار العمل (مدير أم مفتش)
    if is_manager(request.user):
        FormClass = ManagerCompanyForm
        ImageFormSet = None  # المدير لا يعدل الصور
        is_inspector_flow = False
        
    elif is_inspector(request.user) and company.assigned_to == request.user:
        if company.status_by_inspector in ['accepted', 'in_progress']:
            FormClass = InspectorCompanyForm
            ImageFormSet = inlineformset_factory(Company, CompanyImage, form=CompanyImageForm, extra=1, can_delete=True)
            is_inspector_flow = True
        else:
            # منع التعديل إذا كانت الحالة ليست 'accepted' أو 'in_progress'
            messages.error(request, "يجب قبول المهمة أولاً قبل تعديل بياناتها الميدانية.")
            return redirect('companies_list')
        
    else:
        messages.error(request, "ليس لديك الصلاحية لتعديل هذه المنشأة.")
        return redirect('companies_list')

    # 2. التعامل مع طلب POST
    if request.method == 'POST':
        form = FormClass(request.POST, request.FILES, instance=company)
        formset = ImageFormSet(request.POST, request.FILES, instance=company) if ImageFormSet else None

        # التحقق من صحة النموذج والـ formset (إذا كان موجوداً)
        if form.is_valid() and (not formset or formset.is_valid()):
            # الحصول على القيمة الجديدة من الفورم
            new_assigned_to = form.cleaned_data.get('assigned_to')
            
            # طباعة القيم للمساعدة في التصحيح
            print(f"Original assigned_to: {original_assigned_to}")
            print(f"New assigned_to: {new_assigned_to}")
            print(f"Comparison: {original_assigned_to != new_assigned_to}")
            
            # حفظ الفورم
            company = form.save()
            
            # حفظ الـ formset إذا كان موجوداً
            if formset:
                formset.save()

            # تحديث حالة المفتش إذا كان في وضع المفتش
            if is_inspector_flow and company.status_by_inspector == 'accepted':
                company.status_by_inspector = 'in_progress'
                company.save()
                
            # منطق المدير (إعادة التعيين والإشعار)
            if not is_inspector_flow:
                # المقارنة بين القيمة الأصلية والجديدة
                if original_assigned_to != new_assigned_to:
                    print(f"Sending notifications - Old: {original_assigned_to}, New: {new_assigned_to}")
                    
                    # إشعار للمفتش القديم (إذا كان هناك مفتش قديم)
                    if original_assigned_to:
                        create_notification(
                            recipient=original_assigned_to,
                            sender=request.user,
                            title="إلغاء تعيين مهمة",
                            message=f"قام المدير {request.user.username} بإلغاء تعيين منشأة {company.company_name} منك.",
                            company=company
                        )
                    
                    # إشعار للمفتش الجديد (إذا كان هناك مفتش جديد)
                    if new_assigned_to:
                        company.status_by_inspector = 'assigned'
                        company.save()  # حفظ حالة assigned
                        create_notification(
                            recipient=new_assigned_to,
                            sender=request.user,
                            title="تم تعيين منشأة جديدة لك",
                            message=f"قام المدير {request.user.username} بتعيين منشأة {company.company_name} لك. يرجى تأكيد الاستلام.",
                            company=company
                        )
                        send_assignment_notification(company)
                    else:
                        # لا يوجد مفتش معين
                        company.status_by_inspector = 'not_assigned'
                        company.save()  # حفظ حالة not_assigned

            messages.success(request, f"تم تحديث بيانات منشأة {company.company_name} بنجاح.")
            return redirect('companies_list')
        else:
            # إذا كان الفورم غير صالح، عرض الأخطاء
            messages.error(request, "يوجد أخطاء في البيانات المرسلة. يرجى التصحيح والمحاولة مرة أخرى.")
    
    # 3. التعامل مع طلب GET
    else:
        form = FormClass(instance=company)
        formset = ImageFormSet(instance=company) if ImageFormSet else None
    
    context = {
        'form': form,
        'formset': formset,
        'company': company,
        'is_inspector_flow': is_inspector_flow
    }
    return render(request, 'inspectors/edit_company.html', context)
    
    
    




@login_required(login_url='login')
def add_inspection_view(request, pk):
    company = get_object_or_404(Company, pk=pk)
    
    if request.method == 'POST':
        inspection_form = InspectionForm(request.POST)
        image_formset = InspectionImageFormSet(request.POST, request.FILES, prefix='images')

        if inspection_form.is_valid() and image_formset.is_valid():
            try:
                with transaction.atomic():
                    # حفظ التقرير وربطه بالمستخدم والشركة
                    inspection = inspection_form.save(commit=False)
                    inspection.inspector = request.user
                    inspection.company = company
                    inspection.status = 'draft'
                    inspection.save()
                    
                    # حفظ الصور وربطها بالتقرير الجديد
                    images = image_formset.save(commit=False)
                    for image in images:
                        image.inspection = inspection
                        image.save()

                return redirect('inspection_report_detail', pk=inspection.pk)
            except Exception as e:
                inspection_form.add_error(None, f"حدث خطأ أثناء الحفظ: {str(e)}")
    else:
        inspection_form = InspectionForm()
        image_formset = InspectionImageFormSet(prefix='images')

    context = {
        'company': company,
        'inspection_form': inspection_form,
        'image_formset': image_formset,
    }
    return render(request, 'inspectors/add_inspection_report.html', context)


@login_required(login_url='login')
def inspection_report_detail_view(request, pk):
    inspection = get_object_or_404(Inspection, pk=pk)
    images = InspectionImage.objects.filter(inspection=inspection)
    
    context = {
        'inspection': inspection,
        'company': inspection.company, # لتسهيل الوصول لبيانات الشركة
        'images': images,
    }
    return render(request, 'inspectors/inspection_report_detail.html', context)




@login_required(login_url='login')
def generate_inspection_pdf_view(request, pk):
    inspection = get_object_or_404(Inspection, pk=pk)
    
    context = {
        'inspection': inspection,
        'company': inspection.company,
    }

    # رندر القالب إلى HTML
    html_string = render_to_string('inspectors/inspection_report_pdf.html', context)
    
    # إنشاء ملف في الذاكرة (Buffer)
    result = io.BytesIO()
    
    # تحويل الـ HTML إلى PDF
    pdf = pisa.pisaDocument(io.BytesIO(html_string.encode("UTF-8")), result)
    
    if not pdf.err:
        response = HttpResponse(result.getvalue(), content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="inspection_report_{inspection.pk}.pdf"'
        return response
        
    return HttpResponse("حدث خطأ أثناء إنشاء ملف الـ PDF", status=400)

@login_required(login_url='login')
def soft_delete_inspection_view(request, pk):
    # إذا كان المستخدم مديرًا، يسمح له بالحذف
    if is_manager(request.user):
        inspection = get_object_or_404(Inspection, pk=pk) # ✅ المدير يحذف أي تقرير
        
    # إذا كان المستخدم مفتشًا، يجب أن يكون هو المالك للتقرير
    elif is_inspector(request.user):
        inspection = get_object_or_404(Inspection, pk=pk, inspector=request.user) # ✅ المفتش يحذف تقاريره فقط
        if inspection.status == 'draft':
            pass
        else:
            # منع الحذف إذا كان قيد المراجعة، مؤرشف، أو مرفوض
            messages.error(request, "لا يمكنك حذف هذا التقرير إلا إذا كان في حالة **المسودة**.")
            return redirect('inspection_report_detail', pk=inspection.pk)
        
    else:
        messages.error(request, "ليس لديك الصلاحية لحذف هذا التقرير.")
        return redirect('home')

    # تأكدي من أن التقرير ليس بالفعل محذوفًا
    if inspection.status == 'deleted':
        messages.warning(request, "التقرير محذوف بالفعل.")
        return redirect('company_details', pk=inspection.company.pk)
        
    # تطبيق الحذف الناعم
    inspection.status = 'deleted'
    inspection.save()
    messages.success(request, "تم حذف التقرير ناعمًا بنجاح.")
    return redirect('company_details', pk=inspection.company.pk)





@login_required(login_url='login')
def edit_inspection_view(request, pk):
    inspection = get_object_or_404(Inspection, pk=pk, inspector=request.user)

    if inspection.status != 'draft':
        messages.error(request, "لا يمكن تعديل التقرير إلا في حالة المسودة.")
        return redirect('inspection_report_detail', pk=inspection.pk)
    
    if request.method == 'POST':
        form = InspectionForm(request.POST, instance=inspection)
        formset = InspectionImageFormSet(request.POST, request.FILES, instance=inspection, prefix='images')
        
        if form.is_valid() and formset.is_valid():
            form.save()
            formset.save()
            messages.success(request, "تم تعديل التقرير بنجاح.")
            return redirect('inspection_report_detail', pk=inspection.pk)
        else:
            messages.error(request, "حدث خطأ أثناء حفظ التعديلات. الرجاء مراجعة البيانات.")
    else:
        form = InspectionForm(instance=inspection)
        formset = InspectionImageFormSet(instance=inspection, prefix='images')
        
    context = {
        'inspection': inspection,
        'form': form,
        'formset': formset
    }
    return render(request, 'inspectors/edit_inspection.html', context)


@login_required(login_url='login')
def submit_for_review_view(request, pk):
    # ✅ التأكد من أنه المفتش المالك و أن الحالة هي 'draft'
    inspection = get_object_or_404(Inspection, pk=pk, inspector=request.user, status='draft')
    
    
    if request.method == 'POST':
        inspection.status = 'pending_approval'
        inspection.save()
        # ✅ إشعار للمدير (يجب تنفيذ دالة الإشعار هنا)
        create_notification(recipient=inspection.company.manager, sender= request.user, title="تقرير جديد للمراجعة", message= f"باكمال التقرير الخاص بشركة {inspection.company.company_name} {request.user} قام المفنش" , company= inspection.company)
        messages.success(request, "تم إرسال التقرير للمراجعة بنجاح. لا يمكن تعديله الآن.")
        return redirect('inspection_report_detail', pk=inspection.pk)
    
    return redirect('inspection_report_detail', pk=inspection.pk) # يمكن أن تكون صفحة تأكيد

@login_required(login_url='login')
@user_passes_test(is_inspector)
def inspector_rejected_reports_view(request):
    """
    يعرض للمفتش قائمة بالتقارير التي تم رفضها من المدير وتحتاج إلى تعديل.
    """
    # جلب التقارير المرفوضة التي تخص هذا المفتش فقط
    inspections = Inspection.objects.filter(
        inspector=request.user, 
        status='rejected'
    ).order_by('-inspection_date')
    
    context = {
        'inspections': inspections,
        'list_title': 'التقارير المرفوضة (أرشيف)',
    }
    return render(request, 'inspectors/rejected_reports.html', context)



@login_required(login_url='login')
@user_passes_test(is_manager)
def manager_review_list_view(request):
    
    # الاستعلام الأساسي: تقارير بانتظار الموافقة فقط
    inspections = Inspection.objects.filter(
        status='pending_approval'
    ).select_related('inspector', 'company')
    
    # 1. تطبيق البحث (Searching)
    search_query = request.GET.get('q')
    if search_query:
        # البحث في اسم الشركة (company__company_name) أو اسم المفتش (inspector__username أو الاسم الكامل)
        inspections = inspections.filter(
            Q(company__company_name__icontains=search_query) |
            Q(inspector__first_name__icontains=search_query) |
            Q(inspector__last_name__icontains=search_query) |
            Q(inspector__username__icontains=search_query) |
            Q(inspector__user_id__icontains=search_query) 
        )

    # 2. تطبيق التصفية حسب نطاق التاريخ (Date Range Filtering)
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    
    if date_from:
        try:
            # فلترة التفتيش الذي تاريخه أكبر من أو يساوي (>=) تاريخ البداية
            inspections = inspections.filter(inspection_date__gte=date_from)
        except Exception:
            # يمكنك إضافة رسالة خطأ هنا إذا كان تنسيق التاريخ غير صحيح
            pass

    if date_to:
        try:
            # فلترة التفتيش الذي تاريخه أقل من أو يساوي (<=) تاريخ النهاية
            # ملاحظة: إذا كنت تستخدم حقل DateTimeField، قد تحتاج لإضافة نهاية اليوم (23:59:59)
            # ولكن لحقل DateField يكفي استخدام القيمة مباشرة
            inspections = inspections.filter(inspection_date__lte=date_to)
        except Exception:
            # يمكنك إضافة رسالة خطأ هنا
            pass
            

    # 4. تطبيق الترتيب (Ordering)
    order_by = request.GET.get('order_by', '-inspection_date') # الافتراضي: الأحدث أولاً
    
    # التأكد من أن الترتيب صحيح وآمن
    allowed_orders = ['inspection_date', '-inspection_date'] 
    if order_by in allowed_orders:
        inspections = inspections.order_by(order_by)
    else:
        # إذا كانت القيمة غير مسموح بها، نستخدم الترتيب الافتراضي
        inspections = inspections.order_by('-inspection_date')
    
    context = {
        'inspections': inspections, 
        'list_title': 'تقارير بانتظار الموافقة',
        'search_query': search_query,      # لحفظ قيمة البحث
        'date_from': date_from,            # لحفظ قيمة تاريخ البداية
        'date_to': date_to,                # لحفظ قيمة تاريخ النهاية
        'current_order': order_by,              # لحفظ قيمة الترتيب
    }
    return render(request, 'managers/reports_list.html', context)


@login_required(login_url='login')
@user_passes_test(is_manager)
def approve_inspection_view(request, pk):
    inspection = get_object_or_404(Inspection, pk=pk, status='pending_approval')
    
    if request.method == 'POST':
        # 🛑 منطق الأرشفة
        inspection.status = 'archived' # نستخدم Archived بدلاً من Approved مباشرة للأرشفة النهائية
        inspection.save()
        
        # ✅ تحديث حالة الشركة (يجب تنفيذه هنا)
        inspection.company.status = 'archived'
        inspection.company.save()
        
        # ✅ إشعار للمفتش
        create_notification(recipient=inspection.inspector, sender=request.user, title="تمت الموافقة على التقرير", message=f"قام المدير {request.user} بالموافقة على التقرير الخاص بشركة {inspection.company.company_name}")
        
        messages.success(request, f"تمت الموافقة وأرشفة تقرير المنشأة {inspection.company.company_name}.")
        return redirect('manager_review_list')

@login_required(login_url='login')
@user_passes_test(is_manager)
def reject_inspection_view(request, pk):
    inspection = get_object_or_404(Inspection, pk=pk, status='pending_approval')
    
    if request.method == 'POST':
        form = DeclineReasonForm(request.POST) # ✅ استخدام نموذج سبب الرفض
        if form.is_valid():
            # 🛑 الرفض يعيد التقرير إلى حالة مرفوض، ويمكن للمفتش التعديل عليها إذا كانت سياستك تسمح بذلك
            # يمكنكِ هنا حفظ سبب الرفض في حقل جديد في نموذج Inspection (مثل rejection_notes)
            
            inspection.status = 'rejected'
            inspection.rejection_notes = form.cleaned_data.get('reason', 'لا يوجد ملاحظات.') # ⚠️ افتراض وجود حقل
            inspection.save()
            
            # ✅ إشعار للمفتش
            create_notification(recipient=inspection.inspector, sender=request.user, title="تم رفض التقرير", 
                                message=f"قام المدير {request.user} برفض التقرير الخاص بشركة {inspection.company.company_name}. الملاحظات: {inspection.rejection_notes}")
            
            messages.success(request, "تم رفض التقرير وإرساله للمفتش للمراجعة.")
            return redirect('manager_review_list')
        
    else:
        form = DeclineReasonForm()
        
    # يجب عرض صفحة الرفض لجمع السبب
    context = {'inspection': inspection, 'form': form}
    return render(request, 'managers/reject_inspection.html', context)


@login_required(login_url='login')
def inspector_completed_reports_view(request):
    # ✅ المفتش يرى فقط تقاريره التي تم أرشفتها
    inspections = Inspection.objects.filter(
        inspector=request.user, 
        status='archived'
    ).select_related('company')
    
    context = {'inspections': inspections, 'list_title': 'تقاريري المنجزة والمؤرشفة'}
    return render(request, 'inspectors/completed_reports.html', context)


@login_required(login_url='login')
@user_passes_test(is_manager) 
def manager_reports_archive_view(request):
    query = request.GET.get('q', '')
    start_date_str = request.GET.get('start_date', '')
    end_date_str = request.GET.get('end_date', '')
    sort_order = request.GET.get('sort_order', '-inspection_date')

    inspections = Inspection.objects.filter(status__in=['approved', 'archived', 'rejected']).select_related('company', 'inspector')
    if query:
        inspections = inspections.filter(Q(company__company_name__icontains=query) |
                                        Q(inspector__username__icontains=query) | 
                                        Q(inspector__user_id__icontains=query))

    if start_date_str:
        start_date = parse_date(start_date_str)
        if start_date:
            inspections = inspections.filter(inspection_date__date__gte=start_date)
        else:
            messages.error(request, "صيغة تاريخ البداية غير صحيحة.")

    if end_date_str:
        end_date = parse_date(end_date_str)
        if end_date:
            inspections = inspections.filter(inspection_date__date__lte=end_date)
        else:
            messages.error(request, "صيغة تاريخ النهاية غير صحيحة.")
    
    inspections = inspections.order_by(sort_order)
    

    
    context = {
        'inspections': inspections, 
        'list_title': 'التقارير المؤرشفة والموافق عليها',
        'query': query,
        'start_date': start_date_str,
        'end_date': end_date_str,
        'sort_order': sort_order,

    }
    return render(request, 'managers/reports_archive.html', context) # قد تحتاج إلى قالب منفصل للمدير


@login_required(login_url='login')
@user_passes_test(is_manager) 
def manager_deleted_reports_view(request):
    
    # 1. الاستعلام الأساسي: عرض التقارير المحذوفة ناعمًا فقط
    deleted_inspections = Inspection.objects.filter(status='deleted').select_related('company', 'inspector')
    
    # 2. تطبيق البحث (Searching)
    search_query = request.GET.get('q')
    if search_query:
        # البحث في: اسم الشركة، اسم المفتش، رقم هوية المفتش
        deleted_inspections = deleted_inspections.filter(
            Q(company__company_name__icontains=search_query) |
            Q(inspector__first_name__icontains=search_query) |
            Q(inspector__last_name__icontains=search_query) |
            Q(inspector__username__icontains=search_query) |
            Q(inspector__user_id__icontains=search_query) # البحث برقم هوية المفتش
        )

    # 3. تطبيق التصفية حسب نطاق التاريخ (Date Range Filtering) - تاريخ الحذف (updated_at)
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    
    if date_from:
        try:
            # فلترة التفتيش الذي تاريخه أكبر من أو يساوي (>=) تاريخ البداية
            deleted_inspections = deleted_inspections.filter(updated_at__date__gte=date_from)
        except Exception:
            pass

    if date_to:
        try:
            # فلترة التفتيش الذي تاريخه أقل من أو يساوي (<=) تاريخ النهاية
            deleted_inspections = deleted_inspections.filter(updated_at__date__lte=date_to)
        except Exception:
            pass
            
    # 4. تطبيق الترتيب (Ordering)
    order_by = request.GET.get('order_by', '-updated_at') # الافتراضي: الأحدث أولاً
    
    # التأكد من أن الترتيب صحيح وآمن
    allowed_orders = ['updated_at', '-updated_at'] 
    if order_by in allowed_orders:
        deleted_inspections = deleted_inspections.order_by(order_by)
    else:
        # إذا كانت القيمة غير مسموح بها، نستخدم الترتيب الافتراضي
        deleted_inspections = deleted_inspections.order_by('-updated_at')
    
    context = {
        'inspections': deleted_inspections, 
        'list_title': 'سلة المحذوفات',
        'search_query': search_query,
        'date_from': date_from,
        'date_to': date_to,
        'current_order': order_by, # لحفظ الترتيب الحالي في القالب
    }
    return render(request, 'managers/deleted_reports.html', context)


@login_required(login_url='login')
@user_passes_test(is_manager)
def restore_inspection_view(request, pk):
    # ✅ استرجاع تقرير محذوف
    inspection = get_object_or_404(Inspection, pk=pk, status='deleted')
    
    if request.method == 'POST':
        # 🛑 إعادة التقرير إلى حالة المسودة للسماح بالتعديل أو المراجعة
        inspection.status = 'draft' 
        inspection.save()
        messages.success(request, "تم استرجاع التقرير بنجاح، حالته الآن مسودة (Draft).")
        return redirect('manager_deleted_reports')
    

@login_required(login_url='login')
def profile_view(request):
    user = User
    
    context = {
        'user': user,
    }
    
    return render(request, 'profiles/profile_detail.html', context)



@login_required(login_url='login')
def manager_audit_log_view(request):
    # 1. تحديد المستخدمين المشرف عليهم المدير الحالي
    supervised_users = request.user.supervised_inspectors.all()
    actor_ids = list(supervised_users.values_list('id', flat=True))
    actor_ids.append(request.user.id)
    
    # 2. الاستعلام الأساسي: سجلات المدير والمفتشين التابعين
    audit_logs = LogEntry.objects.filter(
        actor_id__in=actor_ids
    ).select_related(
        'actor', 
        'content_type'
    )
    
    # 3. تطبيق البحث (Searching)
    search_query = request.GET.get('q')
    if search_query:
        audit_logs = audit_logs.filter(
            # البحث في اسم المستخدم الذي قام بالعملية (actor)
            Q(actor__first_name__icontains=search_query) |
            Q(actor__last_name__icontains=search_query) |
            Q(actor__username__icontains=search_query) |
            Q(actor__user_id__icontains=search_query) |
            
            # البحث في تمثيل السجل المتأثر (مثل اسم المنشأة)
            Q(object_repr__icontains=search_query)
        )

    # 4. تطبيق التصفية حسب نوع العملية (Action)
    filter_action = request.GET.get('action')
    if filter_action:
        # تأكد أن القيمة رقمية لأن log.action يحفظ رقم (0=CREATE, 1=UPDATE, 2=DELETE)
        try:
            action_value = int(filter_action)
            audit_logs = audit_logs.filter(action=action_value)
        except ValueError:
            pass # تجاهل إذا لم يكن رقماً صحيحاً

    # 5. تطبيق التصفية حسب نوع النموذج (Model)
    filter_model = request.GET.get('model')
    if filter_model:
        # ContentType__model يطابق اسم النموذج بالأحرف الصغيرة (مثل 'company' أو 'user')
        audit_logs = audit_logs.filter(content_type__model__iexact=filter_model)
    
    # الترتيب النهائي
    audit_logs = audit_logs.order_by('-timestamp')
    
    # 6. تمرير البيانات إلى الـ Template
    context = {
        'logs': audit_logs,
        'page_title': 'سجلات تدقيق الفريق',
        'search_query': search_query,
        'filter_action': filter_action,
        'filter_model': filter_model,
        # لتوليد قائمة بالنماذج المتاحة في فلتر القالب
        'available_models': ['Company', 'Inspection', 'User'] # أضيفي جميع النماذج التي تُسجَّل
    }
    
    return render(request, 'inspectors/manager_audit_log.html', context)