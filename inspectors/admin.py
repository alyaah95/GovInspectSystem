from django.contrib import admin
from .models import Company, CompanyImage, Inspection, InspectionImage, User
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.sites.shortcuts import get_current_site
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django.contrib.auth.tokens import default_token_generator
from django.utils.translation import gettext_lazy as _
from .forms import CustomUserCreationForm
from auditlog.models import LogEntry

# تسجيل الموديلات الأخرى
admin.site.register(Company)
admin.site.register(CompanyImage)
admin.site.register(Inspection)
admin.site.register(InspectionImage)

User = get_user_model()

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    add_form = CustomUserCreationForm
    
    
    readonly_fields = ("last_login", "date_joined")
    
    fieldsets = (
        (None, {"fields": ("username", "password")}),
        (_("Personal info"), {"fields": ("first_name", "last_name", "email", "phone_number", "address", "user_id")}),
        (
            _("Permissions"),
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                ),
            },
        ),
        (_("Important dates"), {"fields": ("last_login",)}),
    )

    add_fieldsets = (
        (None, {"fields": ("username", "email")}),
        (_("Personal info"), {"fields": ("first_name", "last_name", "phone_number", "address", "user_id")}),
    )

    list_display = ("username", "email", "first_name", "last_name", "is_staff", "is_superuser")
    search_fields = ("username", "first_name", "last_name", "email", "user_id")
    ordering = ("username",)
    
    def save_model(self, request, obj, form, change):
        if not change:
            if request.user.is_superuser:
                obj.set_unusable_password()
                obj.save()
                
                current_site = get_current_site(request) 
                
                subject = _('تفعيل حسابك في GovInspectSystem')
                
                message = render_to_string('inspectors/activation_email.html', {
                    'user': obj,
                    'domain': current_site.domain,
                    'uid': urlsafe_base64_encode(force_bytes(obj.pk)),
                    'token': default_token_generator.make_token(obj),
                })
                
                email = EmailMessage(subject, message, to=[obj.email])
                email.send()
                
                return
        
        super().save_model(request, obj, form, change)

class CustomLogEntryAdmin(admin.ModelAdmin):
    list_display = ['timestamp', 'action', 'content_type', 'object_repr', 'actor']
    
try:
    admin.site.unregister(LogEntry)
    admin.site.register(LogEntry, CustomLogEntryAdmin)
except Exception:
    pass