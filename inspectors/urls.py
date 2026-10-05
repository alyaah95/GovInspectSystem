# inspectors/urls.py
from django.contrib.auth import views as auth_views
from .forms import InspectorSetPasswordForm
from django.urls import path
from . import views

urlpatterns = [
    # routes for user registration and authentication
    path('add-inspector/', views.add_inspector_view, name='add_inspector'),

     # the route for the inspector to view their own profile
    path('profile/', views.profile_detail_view, name='user_profile'),
    
    # the route for the inspector to edit their own profile
    path('profile/edit/', views.edit_profile_view, name='edit_my_profile'),

    # 1. list of all inspectors (for managers to view and manage)
    path('managers/inspectors/', views.inspectors_list_view, name='inspectors_list'),
    
    # 2. inspector detail view (for managers to view an inspector's details)
    path('managers/inspectors/<int:pk>/', views.inspector_detail_view, name='inspector_detail'),

    # the route for the manager to edit an inspector's profile
    path('manager/inspector/<int:pk>/edit/', views.manager_edit_inspector_view, name='manager_edit_inspector'),

    path('manager/audit-logs/', views.manager_audit_log_view, name='manager_audit_logs'),
    
    # company-related routes
    path('companies/', views.companies_list, name='companies_list'),
    path('companies/add/', views.add_company_view, name='add_company'),
    path('companies/<int:pk>/', views.company_details_view, name='company_details'),
    path('companies/<int:pk>/edit/', views.edit_company_view, name='edit_company'), 
    path('companies/<int:pk>/hide/', views.hide_company_view, name='hide_company'),
    path('companies/<int:pk>/show/', views.show_company_view, name='show_company'),
    path('hidden_companies/', views.hidden_companies_list, name='hidden_companies_list'),
    path('companies/<int:pk>/accept/', views.accept_assignment_view, name='accept_assignment'),
    path('companies/<int:pk>/decline/', views.decline_assignment_view, name='decline_assignment'),
    # path('companies/<int:pk>/decline/reason/', views.decline_assignment_view, name='decline_assignment'), 
    path('notifications/', views.notifications_view, name='notifications_view'),
    
    # reports-related routes
    # 1. reports pending review (for managers to review and approve/reject)
    path('reports/review/', views.manager_review_list_view, name='manager_review_list'), # ✅ جديد
    path('reports/review/<int:pk>/approve/', views.approve_inspection_view, name='approve_inspection'), # ✅ جديد
    path('reports/review/<int:pk>/reject/', views.reject_inspection_view, name='reject_inspection'), # ✅ جديد

     # 2. the route for the manager to view all reports (approved, rejected, pending, archived, deleted)
    path('reports/archive/', views.manager_reports_archive_view, name='reports_archive'),
    path('reports/deleted/', views.manager_deleted_reports_view, name='manager_deleted_reports'), # ✅ جديد
    
    
    path('inspection/<int:pk>/', views.inspection_report_detail_view, name='inspection_report_detail'),
    path('inspection/<int:pk>/pdf/', views.generate_inspection_pdf_view, name='generate_inspection_pdf'),
    path('companies/<int:pk>/add-inspection/', views.add_inspection_view, name='add_inspection'), # تم تعديل المسار
    path('inspection/<int:pk>/hide/', views.soft_delete_inspection_view, name='soft_delete_inspection'), # مسار لإخفاء التقرير
    path('inspection/<int:pk>/restore/', views.restore_inspection_view, name='restore_inspection'), # المسار الجديد للاسترجاع
    path('inspection/<int:pk>/edit/', views.edit_inspection_view, name='edit_inspection'),

    # a route for the inspector to submit their inspection report for review (changes status from draft to pending approval)
    path('inspection/<int:pk>/submit/', views.submit_for_review_view, name='submit_for_review'),
    
    # 4. completed and rejected reports for inspectors to view their own reports
    path('inspector/completed-reports/', views.inspector_completed_reports_view, name='inspector_completed_reports'), # ✅ جديد
    path('inspector/rejected-reports/', views.inspector_rejected_reports_view, name='inspector_rejected_reports'),
    
    # the routes for password reset functionality
    path('password_reset/', auth_views.PasswordResetView.as_view(
    template_name='inspectors/password_reset_form.html',
    # the email template for the password reset email
    email_template_name='inspectors/password_reset_email.txt', 
    # the subject template for the password reset email
    html_email_template_name='inspectors/password_reset_email.html',
    subject_template_name='inspectors/password_reset_subject.txt'
    ), name='password_reset'),
    
    path('password_reset/done/', auth_views.PasswordResetDoneView.as_view(template_name='inspectors/password_reset_done.html'), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(template_name='inspectors/password_reset_confirm.html', form_class=InspectorSetPasswordForm), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(template_name='inspectors/password_reset_complete.html'), name='password_reset_complete'),
]

