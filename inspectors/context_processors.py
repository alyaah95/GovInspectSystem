from .models import Notification

def unread_notifications(request):
    """
    يقوم بجلب عدد الإشعارات غير المقروءة للمستخدم الحالي.
    ويضيف هذا العدد كمتغير إلى سياق جميع القوالب.
    """
    if request.user.is_authenticated:
        # 1. count the unread notifications for the current user
        unread_count = Notification.objects.filter(
            recipient=request.user, 
            is_read=False
        ).count()
        
        # 2. return the count in the context
        return {
            'unread_notifications_count': unread_count
        }
    
    # 3. if the user is not authenticated, return 0
    return {
        'unread_notifications_count': 0
    }
