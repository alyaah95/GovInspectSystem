from .models import Notification # تأكدي من استيراد موديل Notification من مكان وجوده الصحيح

def unread_notifications(request):
    """
    يقوم بجلب عدد الإشعارات غير المقروءة للمستخدم الحالي.
    ويضيف هذا العدد كمتغير إلى سياق جميع القوالب.
    """
    if request.user.is_authenticated:
        # 1. جلب عدد الإشعارات غير المقروءة للمستخدم المسجل دخوله
        unread_count = Notification.objects.filter(
            recipient=request.user, 
            is_read=False
        ).count()
        
        # 2. إرجاع القيمة في السياق (Context)
        return {
            'unread_notifications_count': unread_count
        }
    
    # إذا لم يكن المستخدم مسجل الدخول، لا نرجع شيئاً
    return {
        'unread_notifications_count': 0
    }
