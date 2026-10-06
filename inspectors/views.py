import os
from django.shortcuts import render, redirect, get_object_or_404
from .forms import CompanyImageFormSet, InspectorCreationForm, CompanyImageForm, ManagerCompanyForm, InspectorCompanyForm, InspectionForm, InspectionImageFormSet, InspectorAuthenticationForm, DeclineReasonForm, UserProfileEditForm
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
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import arabic_reshaper
from bidi.algorithm import get_display

import io
from datetime import date
from auditlog.models import LogEntry
from django.contrib.contenttypes.models import ContentType


from django.contrib.auth import get_user_model
User = get_user_model()




def home(request):
    user = request.user

    # 0. if the user is not authenticated, show them the counts as 0
    if not user.is_authenticated:
        companies_count = Company.objects.filter(status='active').count()
        pending_inspections_count = 0
        inspectors_count = 0

    # 1. if the user is a superuser, show them all counts
    elif user.is_superuser:
        companies_count = Company.objects.filter(status='active').count()
        pending_inspections_count = Inspection.objects.filter(status='pending_approval').count()
        inspectors_count = User.objects.filter(supervisor__isnull=False, is_superuser=False).count()

    # 2. if the user is a manager, show them counts related to their own inspectors and companies
    elif user.groups.filter(name='Managers').exists():
        companies_count = Company.objects.filter(manager=user, status='active').count()
        pending_inspections_count = Inspection.objects.filter(
            company__manager=user, 
            status='pending_approval'
        ).count()
        inspectors_count = user.supervised_inspectors.count()

    # 3. if the user is an inspector, show them counts related to their own assignments
    else:
        companies_count = Company.objects.filter(assigned_to=user, status='active').count()
        pending_inspections_count = Inspection.objects.filter(
            inspector=user, 
            status='pending_approval'
        ).count()
        inspectors_count = 0

    context = {
        'companies_count': companies_count,
        'pending_inspections_count': pending_inspections_count,
        'inspectors_count': inspectors_count,
    }
    return render(request, 'inspectors/home.html', context)


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
    if not user.is_authenticated:
        return False
    # the superuser is treated as a manager for the purpose of this check
    return user.is_superuser or user.groups.filter(name='Managers').exists()

def is_inspector(user):
    if not user.is_authenticated:
        return False
    return user.groups.filter(name='Inspectors').exists()

def is_system_user(user):
    if not user.is_authenticated:
        return False
    # the superuser or any user in the groups
    return user.is_superuser or user.groups.filter(name__in=['Managers', 'Inspectors']).exists()

# a function to send an email notification to the assigned inspector when a company is assigned to them
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

# a function to create a notification in the system for a user
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
            return redirect('inspectors_list')
    else:
        form = InspectorCreationForm()
    return render(request, 'inspectors/add_inspector.html', {'form': form})


# a function to get the count of unread notifications for a user
@login_required(login_url='login')
def profile_detail_view(request):
    # there is no need to check if the user is authenticated here because of the @login_required decorator
    
    context = {
        'user': request.user,
    }
    return render(request, 'profiles/profile_detail.html', context)


from django.db.models import Q # this import for using or in the search

@login_required(login_url='login')
@user_passes_test(is_manager)
def inspectors_list_view(request):
    # 1. Primary Query: Retrieve inspectors reporting to the manager.
    if request.user.is_superuser:
        inspectors = User.objects.filter(groups__name='Inspectors')
    else:
        inspectors = User.objects.filter(groups__name='Inspectors', supervisor=request.user)

    # 2. search functionality: filter inspectors based on the search query across multiple fields
    search_query = request.GET.get('q')
    if search_query:
        # apply the search filter using Q objects for OR conditions
        inspectors = inspectors.filter(
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(username__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(user_id__icontains=search_query) 
        )

    # 3. applying status filter (active/inactive) if provided in the GET parameters
    filter_status = request.GET.get('status') 
    if filter_status:
        if filter_status == 'active':
            inspectors = inspectors.filter(is_active=True)
        elif filter_status == 'inactive':
            inspectors = inspectors.filter(is_active=False)
    
    # 4. applying ordering based on the 'order_by' GET parameter, with a default order if not provided
    
    # default order is by last_name ascending
    default_order = 'last_name' 
    order_by = request.GET.get('order_by', default_order)

    # define a list of allowed fields for ordering to prevent SQL injection or errors
    # the allowed fields are: last_name, username, date_joined, is_active (both ascending and descending)
    allowed_orders = ['last_name', '-last_name', 'username', '-username', 'date_joined', '-date_joined', '-is_active', 'is_active'] 
    
    if order_by in allowed_orders:
        inspectors = inspectors.order_by(order_by)
    else:
        # if the provided order_by is not allowed, fall back to the default order
        inspectors = inspectors.order_by(default_order)

    if not inspectors.exists():
        messages.info(request, "لا يوجد مفتشون مطابقون لمعايير البحث/التصفية.")
    
    context = {
        'inspectors': inspectors,
        'page_title': 'المفتشون التابعون لي',
        'search_query': search_query, # it is useful to keep the search query in the context to repopulate the search box in the template
        'filter_status': filter_status, # to keep the filter status in the context to repopulate the filter dropdown in the template
        'current_order': order_by,
    }
    return render(request, 'inspectors/inspectors_list.html', context)

@login_required(login_url='login')
@user_passes_test(is_manager)
def inspector_detail_view(request, pk):
    
    # 2. Get inspector data
    inspector = get_object_or_404(User, pk=pk)

    # 3. to make sure that the inspector is supervised by the current manager or the user is a superuser
    # we check if the current user is a superuser or if the inspector's supervisor is the current user
    if not request.user.is_superuser and inspector.supervisor != request.user:
        messages.error(request, "ليس لديك الصلاحية لاستعراض هذا المفتش.")
        return redirect('inspectors_list')
        
    # it is also a good idea to check if the user is actually an inspector, in case the pk is for a user that is not an inspector
    
    context = {
        'inspector': inspector,
        'page_title': f'تفاصيل المفتش: {inspector.get_full_name()}',
    }
    return render(request, 'inspectors/inspector_detail.html', context)


# the function to edit the profile of the current user (inspector or manager)
@login_required(login_url='login')
def edit_profile_view(request):
    if request.method == 'POST':
        # we use instance=request.user to bind the form to the current user's data
        form = UserProfileEditForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'تم تحديث ملفك الشخصي بنجاح. ')
            return redirect('user_profile') # The URL name is assumed to be 'user_profile'.
        else:
            # Form field error messages will appear automatically.
            messages.error(request, 'الرجاء تصحيح الأخطاء في النموذج. ')
    else:
        form = UserProfileEditForm(instance=request.user)

    context = {
        'form': form,
        'page_title': 'تعديل الملف الشخصي',
        'user': request.user, # To enable displaying the username/email in the template
    }
    return render(request, 'profiles/edit_profile.html', context)


@login_required(login_url='login')
@user_passes_test(is_manager) 
def manager_edit_inspector_view(request, pk):
    """
    تسمح للمدير بتعديل بيانات مفتش محدد (باستخدام الـ pk).
    """
    # 1. get the inspector object or return 404 if not found
    inspector = get_object_or_404(User, pk=pk)
    
    # 2. a security check to ensure that the current user is either a superuser or the supervisor of the inspector
    if inspector.supervisor != request.user or inspector.is_superuser or not inspector.groups.filter(name='Inspectors').exists():
        messages.error(request, 'ليس لديك الصلاحية لتعديل بيانات هذا المستخدم، إما لأنه ليس تابعًا لك أو ليس مفتشًا معتمدًا.')
        return redirect('inspectors_list')

    if request.method == 'POST':
        # 3. Binding the form to POST data and the inspector object (instance=inspector)
        form = UserProfileEditForm(request.POST, instance=inspector)
        if form.is_valid():
            form.save()
            messages.success(request, f'تم تعديل بيانات المفتش {inspector.username} بنجاح.')
            return redirect('inspector_detail', pk=inspector.pk) 
        else:
            messages.error(request, 'الرجاء تصحيح الأخطاء في النموذج. ')
    else:
        # 4. Display the form for the first time, pre-filled with the inspector's data.
        form = UserProfileEditForm(instance=inspector)

    context = {
        'form': form,
        'page_title': f'تعديل المفتش: {inspector.username}',
        'user_to_edit': inspector, 
    }
    # Ensure that the template 'inspectors/inspector_edit.html' exists.
    return render(request, 'inspectors/inspector_edit.html', context)



@login_required(login_url='login')
@user_passes_test(is_system_user, login_url='login')
def companies_list(request):
    query = request.GET.get('q', '').strip()
    start_date = request.GET.get('start_date', '').strip()
    end_date = request.GET.get('end_date', '').strip()
    sort_order = request.GET.get('sort_order', '-created_at')

   # Defining permissions within the data-fetching function.
    user = request.user
    
    if user.is_superuser:
        # The superuser sees all active companies in the system.
        companies = Company.objects.filter(status='active')
    elif user.groups.filter(name='Managers').exists():
        companies = Company.objects.filter(manager=user,status='active')
    elif user.groups.filter(name='Inspectors').exists():
        companies = Company.objects.filter(assigned_to=user, status='active')
    else:
        companies = Company.objects.none()

    # Retrieve the number of unread notifications
    unread_notifications_count = Notification.objects.filter(recipient=user, is_read=False).count()

    # Filter by text search
    if query:
        companies = companies.filter(
            Q(company_name__icontains=query) | Q(region__icontains=query)
        )

    # Filter by date
    if start_date and end_date:
        start = parse_date(start_date)
        end = parse_date(end_date)
        if start and end:
            companies = companies.filter(created_at__date__range=(start, end))

    # Apply sorting (ensure that sort_order is a safe value)
    companies = companies.order_by(sort_order)

    context = {
        'companies': companies,
        'query': query,
        'start_date': start_date,
        'end_date': end_date,
        'sort_order': sort_order,
        'unread_notifications_count': unread_notifications_count,
    }
    return render(request, 'inspectors/companies_list.html', context)



# 4. Soft delete (Admin only)
@login_required(login_url='login')
@user_passes_test(is_manager)
def hide_company_view(request, pk):
    company = get_object_or_404(Company, pk=pk)
    company.status = 'deleted'
    company.save()
    if company.assigned_to:
        create_notification(
            recipient=company.assigned_to,
            sender=request.user,
            title='إلغاء مهمة',
            message=f'تم إلغاء المهمة الخاصة بمنشأة "{company.company_name}" وإخفاؤها من قبل المدير.',
            company=company
        )

    messages.success(request, f"تم إخفاء منشأة {company.company_name} بنجاح.")
    return redirect('companies_list')



# 5. List of Hidden Entities (Admin Only)
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


# 6. Restore Hidden Facility (Admin Only)
@login_required(login_url='login')
@user_passes_test(is_manager)
def show_company_view(request, pk):
    company = get_object_or_404(Company, pk=pk)
    company.status = 'active'
    company.save()
    create_notification(
        recipient=company.assigned_to,
        sender=request.user,
        title='استعادة منشأة',
        message=f'تم استعادة المنشأة "{company.company_name}" من قبل المدير.',
        company=company
    )
    messages.success(request, f"تم استعادة منشأة {company.company_name} بنجاح.")
    return redirect('hidden_companies_list')



# 2. Add a new facility (for managers only)
@login_required(login_url='login')
@user_passes_test(is_manager)
def add_company_view(request):
    if request.method == 'POST':
        form = ManagerCompanyForm(request.POST)
        formset = CompanyImageFormSet(request.POST, request.FILES, prefix='images')
        if form.is_valid() and formset.is_valid():
            company = form.save(commit=False)
            company.manager = request.user
            if company.assigned_to: 
                company.status_by_inspector = 'assigned' 
            company.save() # Here, the company acquired an ID.

            # 2. Link the formset to the company and save it directly.
            # This method saves you from creating a manual loop and helps you avoid errors.
            formset.instance = company 
            formset.save()
            # Create an in-system notification
            create_notification(
                recipient=company.assigned_to,
                sender=request.user,
                title="تم تعيين منشأة جديدة لك",
                message=f"قام المدير {request.user.username} بتعيين منشأة {company.company_name} لك. يرجى تأكيد الاستلام.",
                company=company
            )
            send_assignment_notification(company) # Send notification
            messages.success(request, f"تم إضافة منشأة {company.company_name} بنجاح وتم تعيينها للمفتش.")
            return redirect('companies_list')
    else:
        form = ManagerCompanyForm()
        formset = CompanyImageFormSet(prefix='images')
    
    context = {'form': form, 'formset': formset}
    return render(request, 'inspectors/add_company.html', context)


# 3. Accepting the task
@login_required(login_url='login')
@user_passes_test(is_inspector)
def accept_assignment_view(request, pk):
    company = get_object_or_404(Company, pk=pk, assigned_to=request.user)
    company.status_by_inspector = 'accepted'
    company.save()

    # Create a notification for the manager when the inspector accepts the assignment
    create_notification(
        recipient=company.manager,
        sender=request.user,
        title="تم قبول مهمة",
        message=f"المفتش {request.user.username} قام بقبول مهمة {company.company_name}.",
        company=company
    )

    messages.success(request, f"تم قبول مهمة {company.company_name} بنجاح.")
    return redirect('companies_list')

# 4. Declining the task with a reason
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
            
            # Create a notification for the manager when the inspector declines the assignment
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


# 5. Notifications view for the user to see their notifications
@login_required(login_url='login')
@user_passes_test(is_system_user, login_url='login') 
def notifications_view(request):
    notifications = Notification.objects.filter(recipient=request.user).order_by('-created_at')
    
    # Mark all notifications as read when the user views them
    notifications.update(is_read=True)

    return render(request, 'inspectors/notifications.html', {'notifications': notifications})

@login_required(login_url='login')
def company_details_view(request, pk):
    company = get_object_or_404(Company, id=pk)
    if is_manager(request.user):
        pass # the manager can view all companies they manage, so no additional checks are needed here
        
    elif is_inspector(request.user):
        # Check if the inspector is assigned to this company
        if company.assigned_to == request.user:
            pass
        else:
            # If the inspector is not assigned to this company, we can either redirect them or show an error message.
            # then we redirect them to the companies list with an error message.
            messages.error(request, "لم تعد هذه المنشأة مُعيّنة لك.")
            return redirect('companies_list') 
            
    else:
        return redirect('home')
    company_images =  CompanyImage.objects.filter(company=company)
    inspections = Inspection.objects.filter(company=company).exclude(status='deleted').order_by('-inspection_date')
    context = {
        'company': company,
        'inspections': inspections,
        'company_images': company_images
    }
    return render(request, 'inspectors/company_details.html', context)



@login_required(login_url='login')
@user_passes_test(is_system_user, login_url='login')
def edit_company_view(request, pk):
    # Fetch the target company or return a 404 response if not found
    company = get_object_or_404(Company, pk=pk)
    original_assigned_to = company.assigned_to
    
    # Initialize form variables to prevent UnboundLocalError
    FormClass = None
    ImageFormSet = None
    is_inspector_flow = False

    # 1. Determine form class and formset based on the user role
    if is_manager(request.user):
        FormClass = ManagerCompanyForm
        # Fixed the double assignment typo here
        ImageFormSet = inlineformset_factory(Company, CompanyImage, form=CompanyImageForm, extra=1, can_delete=True)
        is_inspector_flow = False
        
    elif is_inspector(request.user) and company.assigned_to == request.user:
        if company.status_by_inspector in ['accepted', 'in_progress']:
            FormClass = InspectorCompanyForm
            ImageFormSet = inlineformset_factory(Company, CompanyImage, form=CompanyImageForm, extra=1, can_delete=True)
            is_inspector_flow = True
        else:
            # Inspector must accept the assignment before editing field data
            messages.error(request, "يجب قبول المهمة أولاً قبل تعديل بياناتها الميدانية.")
            return redirect('companies_list')
        
    else:
        messages.error(request, "ليس لديك الصلاحية لتعديل هذه المنشأة.")
        return redirect('companies_list')

    # 2. Handle POST requests for form submissions
    if request.method == 'POST':
        form = FormClass(request.POST, request.FILES, instance=company)
        formset = ImageFormSet(request.POST, request.FILES, instance=company) if ImageFormSet else None

        # Validate form and formset
        if form.is_valid() and (not formset or formset.is_valid()):
            new_assigned_to = form.cleaned_data.get('assigned_to')
            
            # Save company instance in memory without committing to DB yet
            company = form.save(commit=False)
            
            # Update status if in the inspector workflow
            if is_inspector_flow and company.status_by_inspector == 'accepted':
                company.status_by_inspector = 'in_progress'
            
            # Commit company changes and save many-to-many relationships
            company.save()
            form.save_m2m()
            
            # Save the associated image formset if present
            if formset:
                formset.save()

            # Handle notifications and inspector assignment updates for managers
            if not is_inspector_flow:
                if original_assigned_to != new_assigned_to:
                    # Notify the unassigned inspector
                    if original_assigned_to:
                        create_notification(
                            recipient=original_assigned_to,
                            sender=request.user,
                            title="إلغاء تعيين مهمة",
                            message=f"قام المدير {request.user.username} بإلغاء تعيين منشأة {company.company_name} منك.",
                            company=company
                        )
                    
                    # Notify and assign the new inspector
                    if new_assigned_to:
                        company.status_by_inspector = 'assigned'
                        company.save(update_fields=['status_by_inspector'])
                        
                        create_notification(
                            recipient=new_assigned_to,
                            sender=request.user,
                            title="تم تعيين منشأة جديدة لك",
                            message=f"قام المدير {request.user.username} بتعيين منشأة {company.company_name} لك. يرجى تأكيد الاستلام.",
                            company=company
                        )
                        send_assignment_notification(company)
                    else:
                        # Revert status if unassigned entirely
                        company.status_by_inspector = 'not_assigned'
                        company.save(update_fields=['status_by_inspector'])

            messages.success(request, f"تم تحديث بيانات منشأة {company.company_name} بنجاح.")
            return redirect('company_details', pk=company.pk)
        else:
            messages.error(request, "يوجد أخطاء في البيانات المرسلة. يرجى التصحيح والمحاولة مرة أخرى.")
    
    # 3. Handle GET requests to render form with instance data
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
@user_passes_test(is_system_user, login_url='login')
def add_inspection_view(request, pk):
    company = get_object_or_404(Company, pk=pk)
    
    # Security check: Only the assigned inspector or a manager can add an inspection report for this company.
    if not is_manager(request.user):
        if company.assigned_to != request.user or company.status_by_inspector not in ['accepted', 'in_progress'] or company.status != 'active':
            messages.error(request, " ليس لديك الصلاحية لإضافة تقرير لهذه المنشأة أو يجب قبول المهمة أولاً أو أن المنشأة غير نشطة.")
            return redirect('companies_list')

    if request.method == 'POST':
        inspection_form = InspectionForm(request.POST)
        image_formset = InspectionImageFormSet(request.POST, request.FILES, prefix='images')

        if inspection_form.is_valid() and image_formset.is_valid():
            try:
                with transaction.atomic():
                    inspection = inspection_form.save(commit=False)
                    inspection.inspector = request.user
                    inspection.company = company
                    inspection.status = 'draft'
                    inspection.save()
                    
                    images = image_formset.save(commit=False)
                    for image in images:
                        image.inspection = inspection
                        image.save()
                    
                    # Update the company's status_by_inspector to 'in_progress' if it was 'accepted'
                    if company.status_by_inspector == 'accepted':
                        company.status_by_inspector = 'in_progress'
                        company.save()

                messages.success(request, "تم حفظ المسودة بنجاح.")
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
@user_passes_test(is_system_user, login_url='login')
def inspection_report_detail_view(request, pk):
    inspection = get_object_or_404(Inspection, pk=pk)
    
    # Security check: Only the assigned inspector or a manager can view this inspection report.
    if not is_manager(request.user) and inspection.inspector != request.user:
        messages.error(request, "ليس لديك صلاحية لعرض هذا التقرير.")
        return redirect('companies_list')

    images = InspectionImage.objects.filter(inspection=inspection)
    context = {
        'inspection': inspection,
        'company': inspection.company,
        'images': images,
    }
    return render(request, 'inspectors/inspection_report_detail.html', context)





def generate_inspection_pdf_view(request, pk):
    inspection = get_object_or_404(Inspection, pk=pk)
    company = inspection.company
    
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    # 1. Register the Arabic font for proper rendering of Arabic text in the PDF.
    # Make sure the font file is located in the specified path and is accessible.
    font_path = os.path.join(settings.BASE_DIR, 'static/fonts/Amiri-Regular.ttf')
    pdfmetrics.registerFont(TTFont('ArabicFont', font_path))

    def fix_a(text):
        if not text: return ""
        reshaped = arabic_reshaper.reshape(str(text))
        return get_display(reshaped)

    # draw the header rectangle with a royal red color
    p.setFillColorRGB(0.86, 0.15, 0.15)
    p.rect(width - 45, height - 80, 5, 50, fill=1, stroke=0)

    # draw the title of the report in Arabic
    p.setFillColorRGB(0, 0, 0)
    p.setFont('ArabicFont', 22)
    p.drawRightString(width - 60, height - 60, fix_a("تقرير تفتيش رسمي"))
    
    p.setFont('ArabicFont', 10)
    p.drawString(50, height - 60, f"Date: {inspection.inspection_date.strftime('%Y-%m-%d')}")

    # draw the company name and region
    current_y = height - 120

    def draw_row(label, value, y_pos):
        p.setFont('ArabicFont', 12)
        p.setFillColorRGB(0.3, 0.3, 0.3)
        p.drawRightString(width - 60, y_pos, fix_a(f"{label}:"))
        p.setFillColorRGB(0, 0, 0) 
        p.drawRightString(width - 180, y_pos, fix_a(value))
        p.setStrokeColorRGB(0.9, 0.9, 0.9)
        p.line(50, y_pos - 5, width - 50, y_pos - 5)
        return y_pos - 30

    # show company details
    p.setFont('ArabicFont', 14)
    p.drawRightString(width - 60, current_y, fix_a("• معلومات المنشأة"))
    current_y -= 25
    current_y = draw_row("اسم المنشأة", company.company_name, current_y)
    current_y = draw_row("رقم المنشأة", company.company_number, current_y)
    current_y = draw_row("المنطقة", company.region, current_y)

    # show inspection details
    current_y -= 20
    p.setFont('ArabicFont', 14)
    p.drawRightString(width - 60, current_y, fix_a("• تفاصيل التفتيش"))
    current_y -= 25
    current_y = draw_row("تقدير العمالة", inspection.workers_size_estimation, current_y)
    current_y = draw_row("مطابقة الرخصة", inspection.get_license_compliance_display(), current_y)
    current_y = draw_row("رأي المفتش", inspection.inspector_opinion, current_y)

    # Representative's Details
    current_y -= 20
    p.setFont('ArabicFont', 14)
    p.drawRightString(width - 60, current_y, fix_a("• بيانات المندوب"))
    current_y -= 25
    current_y = draw_row("توقيع المندوب", f"{inspection.mandoub_name_1}", current_y)

    # Finish and Save
    p.showPage()
    p.save()
    buffer.seek(0)
    return HttpResponse(buffer, content_type='application/pdf')

@login_required(login_url='login')
def soft_delete_inspection_view(request, pk):
    # if the user is a manager, they can delete any report
    if is_manager(request.user):
        inspection = get_object_or_404(Inspection, pk=pk) # the manager can delete any report
        
    # if the user is an inspector, they can only delete their own reports
    elif is_inspector(request.user):
        inspection = get_object_or_404(Inspection, pk=pk, inspector=request.user) 
        if inspection.status == 'draft':
            pass
        else:
            # prevent deletion if the report is not in draft status
            messages.error(request, "لا يمكنك حذف هذا التقرير إلا إذا كان في حالة **المسودة**.")
            return redirect('inspection_report_detail', pk=inspection.pk)
        
    else:
        messages.error(request, "ليس لديك الصلاحية لحذف هذا التقرير.")
        return redirect('home')

    # make sure the report is not already deleted
    if inspection.status == 'deleted':
        messages.warning(request, "التقرير محذوف بالفعل.")
        return redirect('company_details', pk=inspection.company.pk)
        
    # Soft delete the inspection report by changing its status to 'deleted'
    inspection.status = 'deleted'
    inspection.save()
    messages.success(request, "تم حذف التقرير ناعمًا بنجاح.")
    return redirect('company_details', pk=inspection.company.pk)





@login_required(login_url='login')
@user_passes_test(is_system_user, login_url='login')
def edit_inspection_view(request, pk):
    # additional security check: only the inspector who created the report can edit it, and only if it's in 'draft' or 'rejected' status
    inspection = get_object_or_404(Inspection, pk=pk, inspector=request.user)

    if inspection.status != 'draft' and inspection.status != 'rejected':
        messages.error(request, "لا يمكن تعديل التقرير إلا إذا كان مسودة أو مرفوضاً من المدير.")
        return redirect('inspection_report_detail', pk=inspection.pk)
    
    if request.method == 'POST':
        form = InspectionForm(request.POST, instance=inspection)
        formset = InspectionImageFormSet(request.POST, request.FILES, instance=inspection, prefix='images')
        
        if form.is_valid() and formset.is_valid():
            form.save()
            formset.save()
            messages.success(request, "تم تحديث التقرير.")
            return redirect('inspection_report_detail', pk=inspection.pk)
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
@user_passes_test(is_inspector)
def submit_for_review_view(request, pk):
    # make sure the inspection report belongs to the current inspector and is in 'draft' status
    inspection = get_object_or_404(Inspection, pk=pk, inspector=request.user, status='draft')
    
    
    if request.method == 'POST':
        inspection.status = 'pending_approval'
        inspection.save()
        # notify the manager that a new report is ready for review
        create_notification(recipient=inspection.company.manager, sender= request.user, title="تقرير جديد للمراجعة", message= f"باكمال التقرير الخاص بشركة {inspection.company.company_name} {request.user} قام المفنش" , company= inspection.company)
        messages.success(request, "تم إرسال التقرير للمراجعة بنجاح. لا يمكن تعديله الآن.")
        return redirect('inspection_report_detail', pk=inspection.pk)
    
    return redirect('inspection_report_detail', pk=inspection.pk) 

@login_required(login_url='login')
@user_passes_test(is_inspector)
def inspector_rejected_reports_view(request):
    """
    يعرض للمفتش قائمة بالتقارير التي تم رفضها من المدير وتحتاج إلى تعديل.
    """
    # get all inspections for the current inspector that have been rejected, ordered by inspection date descending
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
    
    # the main queryset: all inspections that are pending approval, with related inspector and company data to avoid N+1 queries
    inspections = Inspection.objects.filter(
        status='pending_approval'
    ).select_related('inspector', 'company')
    
    # 1. apply search filtering based on the query parameter 'q' from the GET request
    search_query = request.GET.get('q')
    if search_query:
        # search in company name, inspector's first name, last name, username, and user_id (assuming user_id is a field in the User model)
        inspections = inspections.filter(
            Q(company__company_name__icontains=search_query) |
            Q(inspector__first_name__icontains=search_query) |
            Q(inspector__last_name__icontains=search_query) |
            Q(inspector__username__icontains=search_query) |
            Q(inspector__user_id__icontains=search_query) 
        )

    # 2. apply date filtering based on 'date_from' and 'date_to' parameters from the GET request
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    
    if date_from:
        try:
            # filter inspections that have an inspection_date greater than or equal to (>=) the start date
            inspections = inspections.filter(inspection_date__gte=date_from)
        except Exception:
            # add an error message here
            pass

    if date_to:
        try:
            # filter inspections that have an inspection_date less than or equal to (<=) the end date
            inspections = inspections.filter(inspection_date__lte=date_to)
        except Exception:
            # add an error message here
            pass
            

    # 4. apply ordering based on the 'order_by' parameter from the GET request, defaulting to '-inspection_date' (most recent first)
    order_by = request.GET.get('order_by', '-inspection_date')
    
    # make sure the order_by value is one of the allowed values to prevent SQL injection or unexpected behavior
    allowed_orders = ['inspection_date', '-inspection_date'] 
    if order_by in allowed_orders:
        inspections = inspections.order_by(order_by)
    else:
        # if the order_by value is not allowed, default to '-inspection_date'
        inspections = inspections.order_by('-inspection_date')
    
    context = {
        'inspections': inspections, 
        'list_title': 'تقارير بانتظار الموافقة',
        'search_query': search_query,      # to preserve the search query in the template
        'date_from': date_from,            # to preserve the start date in the template
        'date_to': date_to,                # to preserve the end date in the template
        'current_order': order_by,              # to preserve the current order in the template
    }
    return render(request, 'managers/reports_list.html', context)


@login_required(login_url='login')
@user_passes_test(is_manager)
def approve_inspection_view(request, pk):
    inspection = get_object_or_404(Inspection, pk=pk, status='pending_approval')
    
    if request.method == 'POST':
        #  the logic for approving the inspection report and archiving it
        inspection.status = 'archived'
        inspection.save()
        
        # update the company's status to 'archived' as well
        inspection.company.status = 'archived'
        inspection.company.save()
        
        # notify the inspector that their report has been approved and archived
        create_notification(recipient=inspection.inspector, sender=request.user, title="تمت الموافقة على التقرير", message=f"قام المدير {request.user} بالموافقة على التقرير الخاص بشركة {inspection.company.company_name}")
        
        messages.success(request, f"تمت الموافقة وأرشفة تقرير المنشأة {inspection.company.company_name}.")
        return redirect('manager_review_list')

@login_required(login_url='login')
@user_passes_test(is_manager)
def reject_inspection_view(request, pk):
    inspection = get_object_or_404(Inspection, pk=pk, status='pending_approval')
    
    if request.method == 'POST':
        form = DeclineReasonForm(request.POST) 
        if form.is_valid():
            #  Rejection returns the report to a "Rejected" status, and the inspector can modify it if your policy allows.
            # Here, you can save the reason for rejection in a new field within the Inspection form (such as `rejection_notes`).
            
            inspection.status = 'rejected'
            inspection.rejection_notes = form.cleaned_data.get('reason', 'لا يوجد ملاحظات.')
            inspection.save()
            
            # notify the inspector that their report has been rejected, including the reason for rejection
            create_notification(recipient=inspection.inspector, sender=request.user, title="تم رفض التقرير", 
                                message=f"قام المدير {request.user} برفض التقرير الخاص بشركة {inspection.company.company_name}. الملاحظات: {inspection.rejection_notes}")
            
            messages.success(request, "تم رفض التقرير وإرساله للمفتش للمراجعة.")
            return redirect('manager_review_list')
        
    else:
        form = DeclineReasonForm()
        
    # show the rejection form to the manager to provide a reason for rejection
    context = {'inspection': inspection, 'form': form}
    return render(request, 'managers/reject_inspection.html', context)


@login_required(login_url='login')
@user_passes_test(is_inspector)
def inspector_completed_reports_view(request):
    # the inspector only sees their own completed and archived reports, ordered by inspection date descending
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

    inspections = Inspection.objects.filter(status__in=['approved', 'archived']).select_related('company', 'inspector')
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
    return render(request, 'managers/reports_archive.html', context)


@login_required(login_url='login')
@user_passes_test(is_manager) 
def manager_deleted_reports_view(request):
    
    # 1. the main queryset: all inspections that are marked as 'deleted', with related company and inspector data to avoid N+1 queries
    deleted_inspections = Inspection.objects.filter(status='deleted').select_related('company', 'inspector')
    
    # 2. apply search filtering based on the query parameter 'q' from the GET request
    search_query = request.GET.get('q')
    if search_query:
        # search in company name, inspector's first name, last name, username, and user_id (assuming user_id is a field in the User model)
        deleted_inspections = deleted_inspections.filter(
            Q(company__company_name__icontains=search_query) |
            Q(inspector__first_name__icontains=search_query) |
            Q(inspector__last_name__icontains=search_query) |
            Q(inspector__username__icontains=search_query) |
            Q(inspector__user_id__icontains=search_query) 
        )

    # 3. apply date filtering based on 'date_from' and 'date_to' parameters from the GET request
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    
    if date_from:
        try:
            # filter deleted inspections that have an updated_at date greater than or equal to (>=) the start date
            deleted_inspections = deleted_inspections.filter(updated_at__date__gte=date_from)
        except Exception:
            pass

    if date_to:
        try:
            # filter deleted inspections that have an updated_at date less than or equal to (<=) the end date
            deleted_inspections = deleted_inspections.filter(updated_at__date__lte=date_to)
        except Exception:
            pass
            
    # 4. apply ordering based on the 'order_by' parameter from the GET request, defaulting to '-updated_at' (most recent first)
    order_by = request.GET.get('order_by', '-updated_at')
    
    # to make sure the order_by value is one of the allowed values to prevent SQL injection or unexpected behavior
    allowed_orders = ['updated_at', '-updated_at'] 
    if order_by in allowed_orders:
        deleted_inspections = deleted_inspections.order_by(order_by)
    else:
        # if the order_by value is not allowed, default to '-updated_at'
        deleted_inspections = deleted_inspections.order_by('-updated_at')
    
    context = {
        'inspections': deleted_inspections, 
        'list_title': 'سلة المحذوفات',
        'search_query': search_query,
        'date_from': date_from,
        'date_to': date_to,
        'current_order': order_by, # to preserve the current order in the template
    }
    return render(request, 'managers/deleted_reports.html', context)


@login_required(login_url='login')
@user_passes_test(is_manager)
def restore_inspection_view(request, pk):
    # Retrieve the inspection report that is marked as 'deleted' using its primary key (pk). If it doesn't exist, return a 404 error.
    inspection = get_object_or_404(Inspection, pk=pk, status='deleted')
    
    if request.method == 'POST':
        # Restore the inspection report by changing its status back to 'draft'. This allows the inspector to edit and resubmit it.
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
@user_passes_test(is_manager)
def manager_audit_log_view(request):
    # 1. get the list of supervised inspectors for the current manager
    supervised_users = request.user.supervised_inspectors.all()
    actor_ids = list(supervised_users.values_list('id', flat=True))
    actor_ids.append(request.user.id)
    
    # 2. the main queryset: all log entries where the actor is either the manager or one of their supervised inspectors, with related actor and content_type data to avoid N+1 queries
    audit_logs = LogEntry.objects.filter(
        actor_id__in=actor_ids
    ).select_related(
        'actor', 
        'content_type'
    )
    
    # 3. apply search filtering based on the query parameter 'q' from the GET request
    search_query = request.GET.get('q')
    if search_query:
        audit_logs = audit_logs.filter(
            # search in actor's first name, last name, username, and user_id (assuming user_id is a field in the User model)
            Q(actor__first_name__icontains=search_query) |
            Q(actor__last_name__icontains=search_query) |
            Q(actor__username__icontains=search_query) |
            Q(actor__user_id__icontains=search_query) |
            
            # search in the content type's model name (e.g., 'company', 'inspection') and the object representation (object_repr)
            Q(object_repr__icontains=search_query)
        )

    # 4. apply filtering based on the 'action' parameter from the GET request, which corresponds to the action type (0=CREATE, 1=UPDATE, 2=DELETE)
    filter_action = request.GET.get('action')
    if filter_action:
        # to make sure the filter_action value is an integer, we can use a try-except block to catch any ValueError that may occur if the value is not a valid integer
        try:
            action_value = int(filter_action)
            audit_logs = audit_logs.filter(action=action_value)
        except ValueError:
            pass 

    # 5. apply filtering based on the 'model' parameter from the GET request, which corresponds to the model name (e.g., 'company', 'inspection')
    filter_model = request.GET.get('model')
    if filter_model:
        audit_logs = audit_logs.filter(content_type__model__iexact=filter_model)
    
    # the final ordering of the logs is by timestamp descending (most recent first)
    audit_logs = audit_logs.order_by('-timestamp')
    
    final_logs = []
    for log in audit_logs:
        # if the log entry is an UPDATE action and the only change is the 'last_login' field, we skip this log entry and do not add it to the final list
        if log.action == 1 and log.changes and list(log.changes.keys()) == ['last_login']:
            continue  
        
        # if the log entry is an UPDATE action and the 'last_login' field is present in the changes, we remove it from the changes dictionary to avoid displaying it in the audit log
        if log.changes and 'last_login' in log.changes:
            del log.changes['last_login']
            
        final_logs.append(log)
    # 6. pass the final logs and other context variables to the template for rendering
    context = {
        'logs': final_logs,
        'page_title': 'سجلات تدقيق الفريق',
        'search_query': search_query,
        'filter_action': filter_action,
        'filter_model': filter_model,
        # to display the available models in the filter dropdown, we can pass a list of model names to the template. This list can be hardcoded or dynamically generated based on the content types in the database. For simplicity, we will hardcode it here.
        'available_models': ['Company', 'Inspection', 'User'] 
    }
    
    return render(request, 'inspectors/manager_audit_log.html', context)