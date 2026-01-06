# myproject/urls.py
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from inspectors import views as inspectors_views # استيراد الـ views من التطبيق

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # مسارات عامة على مستوى المشروع
    path('', inspectors_views.home, name='home'),
    path('accounts/login/', inspectors_views.login_view, name='login'),
    path('logout/', inspectors_views.logout_view, name='logout'),
    
    # تضمين مسارات تطبيق 'inspectors'
    path('', include('inspectors.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)