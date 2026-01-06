import os
import sys
from django.core.wsgi import get_wsgi_application

# إضافة مسار المشروع للمساعدة في الاستيراد
path = os.path.dirname(os.path.dirname(__file__))
if path not in sys.path:
    sys.path.append(path)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'GovInspectSystem.settings')

application = get_wsgi_application()
app = application