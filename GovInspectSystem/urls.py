# myproject/urls.py
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from inspectors import views as inspectors_views 

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # global paths for login, logout, and home
    path('', inspectors_views.home, name='home'),
    path('accounts/login/', inspectors_views.login_view, name='login'),
    path('logout/', inspectors_views.logout_view, name='logout'),
    
    # include the app's URLs
    path('', include('inspectors.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)