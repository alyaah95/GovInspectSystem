
import os
import sys
import django
import random

from dotenv import load_dotenv
load_dotenv() 

# 1.  Django bootstrap
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "GovInspectSystem.settings")
django.setup()

# Only import models *after* django.setup()
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType

from inspectors.models import (
    Company,
    CompanyImage,
    Inspection,
    InspectionImage,
    Notification,
)

# 2.  Verify Actual Active Database From Django Settings
from django.conf import settings

# to test which database engine is active, we can check the settings
active_db_engine = settings.DATABASES["default"]["ENGINE"]

if "postgresql" in active_db_engine:
    print("[Neon Mode] CONFIRMED: Connected and executing on Neon PostgreSQL.")
elif "sqlite" in active_db_engine:
    print("[Local Mode] CONFIRMED: Connected and executing on local db.sqlite3.")
else:
    print(f"ℹActive Database Engine: {active_db_engine}")

UserModel = get_user_model()

# 3.  Shared constants
SHARED_PASSWORD = "GovInspect@2026"

#Users

SUPERUSER = {
    "username": "alyaa.hassan",
    "email": "alyaa.hassan@gov.eg",
    "first_name": "علياء",
    "last_name": "حسن",
    "phone_number": "01001234567",
    "user_id": "29905141234567",
    "address": "الإسكندرية",
}

# Each manager carries a list of inspectors who belong to their team.
MANAGERS_WITH_TEAMS = [
    {
        "manager": {
            "username": "tareq.awadi",
            "email": "t.awadi@gov.eg",
            "first_name": "طارق",
            "last_name": "العوضي",
            "phone_number": "01101000001",
            "user_id": "28505120000001",
            "address": "القاهرة",
        },
        "inspectors": [
            {
                "username": "majed.abdo",
                "email": "majed.abdo@gov.eg",
                "first_name": "ماجد",
                "last_name": "عبدالرحمن",
                "phone_number": "01201000001",
                "user_id": "29608200000011",
                "address": "الجيزة",
            },
            {
                "username": "iman.shafik",
                "email": "iman.shafik@gov.eg",
                "first_name": "إيمان",
                "last_name": "الشافعي",
                "phone_number": "01201000002",
                "user_id": "29608200000012",
                "address": "الإسكندرية",
            },
            {
                "username": "khaled.mansour",
                "email": "khaled.mansour@gov.eg",
                "first_name": "خالد",
                "last_name": "منصور",
                "phone_number": "01201000003",
                "user_id": "29608200000013",
                "address": "الإسكندرية",
            },
        ],
    },
    {
        "manager": {
            "username": "sameh.gebali",
            "email": "s.gebali@gov.eg",
            "first_name": "سامح",
            "last_name": "الجبالي",
            "phone_number": "01101000002",
            "user_id": "28505120000002",
            "address": "الإسكندرية",
        },
        "inspectors": [
            {
                "username": "rania.mamdouh",
                "email": "rania.mamdouh@gov.eg",
                "first_name": "رانيا",
                "last_name": "ممدوح",
                "phone_number": "01201000004",
                "user_id": "29608200000014",
                "address": "القاهرة",
            },
            {
                "username": "essam.raafat",
                "email": "essam.raafat@gov.eg",
                "first_name": "عصام",
                "last_name": "رأفت",
                "phone_number": "01201000005",
                "user_id": "29608200000015",
                "address": "الجيزة",
            },
            {
                "username": "noha.fathy",
                "email": "noha.fathy@gov.eg",
                "first_name": "نهى",
                "last_name": "فتحي",
                "phone_number": "01201000006",
                "user_id": "29608200000016",
                "address": "الإسكندرية",
            },
        ],
    },
]

# Companies
# Format: (company_name, activity_type, establishment_type, size_m2, workers)
COMPANIES_DATA = [
    # commercial_shop
    ("محل الهدى للملابس",         "بيع تجزئة ملابس جاهزة",          "commercial_shop",     120, 12),
    ("سوبرماركت الأمل",           "تجارة مواد غذائية وبقالة",        "commercial_shop",      85, 8),
    ("مكتبة النور للقرطاسية",     "بيع أدوات مكتبية ومدرسية",        "commercial_shop",      60, 6),
    # commercial_building
    ("عقار الفيصل التجاري",       "تأجير وحدات تجارية ومكتبية",      "commercial_building", 600, 5),
    ("مجمع الأندلس التجاري",      "مركز تجاري متكامل",               "commercial_building", 850, 9),
    # factory
    ("مصنع الشرق للتعبئة",        "تعبئة وتغليف مواد غذائية",        "factory",             300, 45),
    ("مصنع النيل للبلاستيك",      "إنتاج وتشكيل مواد بلاستيكية",     "factory",             250, 38),
    ("مصنع الدلتا للنسيج",        "غزل ونسيج وتصنيع أقمشة",         "factory",             400, 60),
    # lab
    ("معمل التميز للتحاليل",      "مختبر طبي وتحاليل إكلينيكية",     "lab",                  90, 14),
    ("معمل الجودة للمعايرة",      "معايرة واختبار هندسي ومعدني",     "lab",                 110, 11),
    # workshop
    ("ورشة الفنية للخراطة",       "خراطة وتشكيل معادن",              "workshop",             80, 10),
    ("ورشة النجاح للأثاث",        "تصنيع وتشطيب أثاث خشبي",         "workshop",             95, 13),
    # office
    ("مكتب الإخلاص للمقاولات",   "استشارات هندسية ومقاولات عامة",   "office",              150, 20),
    ("مكتب السلام للشحن",         "خدمات شحن وتفريغ وتخزين",        "office",              130, 17),
    # apartment / villa
    ("شقة الأعمال — سموحة",      "مكتب إداري في وحدة سكنية",        "apartment",            70, 4),
    ("فيلا الأعمال — المعمورة",   "مقر شركة محاسبة ومراجعة",        "villa",               200, 7),
]

EGYPTIAN_REGIONS = [
    "سموحة", "سيدي بشر", "المنشية", "العجمي",
    "المعادي", "مصر الجديدة", "الهرم", "شبرا",
    "المنتزه", "محرم بك",
]

STREET_NAMES = [
    "شارع جمال عبدالناصر", "شارع النصر", "شارع الجيش", "شارع فاروق",
    "شارع عمر المختار", "شارع الجمهورية", "شارع طارق", "شارع المحطة",
    "شارع سيدي بشر", "شارع السلام",
]

# Valid inspector_status values for companies that have an assigned inspector
ACTIVE_COMPANY_STATUSES = ["assigned", "accepted", "in_progress"]

# Inspection field pools — drawn deterministically per inspection
COMPLIANCE_POOL         = ["compliant", "non_compliant", "unspecified"]
GENDER_POOL             = ["feasible", "not_feasible", "unspecified"]
VIOLATION_POOL          = ["non_violation", "violation", "unspecified"]
REGULATIONS_POOL        = ["exists", "not_exists", "not_applicable"]
SHIFT_POOL              = ["one_shift", "two_shifts", "three_shifts"]
INSPECTION_STATUS_POOL  = ["draft", "pending_approval", "approved", "rejected"]

# Weighted so most inspections are realistic (mostly compliant)
def _compliance():
    return random.choices(COMPLIANCE_POOL, weights=[70, 20, 10])[0]

def _violation():
    return random.choices(VIOLATION_POOL, weights=[65, 25, 10])[0]

def _regulation():
    return random.choices(REGULATIONS_POOL, weights=[60, 25, 15])[0]

def _gender():
    return random.choices(GENDER_POOL, weights=[50, 40, 10])[0]

def _shift():
    return random.choices(SHIFT_POOL, weights=[50, 35, 15])[0]

def _insp_status():
    return random.choices(INSPECTION_STATUS_POOL, weights=[20, 30, 40, 10])[0]

INSPECTOR_OPINIONS = [
    "المنشأة ملتزمة بكافة اللوائح والقوانين المعمول بها، ولا توجد مخالفات تُذكر.",
    "تم رصد بعض الملاحظات البسيطة وقد أُبلغ صاحب المنشأة لمعالجتها خلال أسبوعين.",
    "المنشأة تعمل بشكل منتظم؛ ويُوصى بتحديث ملفات العمال وتجديد الرخصة.",
    "جاري العمل لتصحيح بعض المخالفات الإجرائية، وقد التزم المسؤول بالتصحيح.",
    "المنشأة في حالة جيدة بصفة عامة مع الحرص على متابعة تطبيق لائحة الجزاءات.",
]

# 4.  Helper functions

def _create_user(data: dict, supervisor=None, is_staff: bool = True) -> "UserModel":
    """Create a single user; skip password hash for set_password."""
    user = UserModel(
        username=data["username"],
        email=data["email"],
        first_name=data["first_name"],
        last_name=data["last_name"],
        phone_number=data["phone_number"],
        user_id=data["user_id"],
        address=data["address"],
        is_staff=is_staff,
        is_active=True,
    )
    if supervisor:
        user.supervisor = supervisor
    user.set_password(SHARED_PASSWORD)
    user.save()
    return user


def setup_groups_and_permissions():
    """
    Create or update the two role groups and assign model-level permissions.

    Managers  → full CRUD on Company + Inspection + Notification
    Inspectors → view-only on Company; full CRUD on Inspection
    """
    print("\n  Setting up groups and permissions …")

    company_ct      = ContentType.objects.get_for_model(Company)
    inspection_ct   = ContentType.objects.get_for_model(Inspection)
    notification_ct = ContentType.objects.get_for_model(Notification)

    all_company_perms      = list(Permission.objects.filter(content_type=company_ct))
    all_inspection_perms   = list(Permission.objects.filter(content_type=inspection_ct))
    all_notification_perms = list(Permission.objects.filter(content_type=notification_ct))
    view_company_perms     = [p for p in all_company_perms if p.codename.startswith("view_")]

    managers_group, _   = Group.objects.get_or_create(name="Managers")
    inspectors_group, _ = Group.objects.get_or_create(name="Inspectors")

    managers_group.permissions.set(
        all_company_perms + all_inspection_perms + all_notification_perms
    )
    inspectors_group.permissions.set(
        view_company_perms + all_inspection_perms
    )

    print(f"    '{managers_group.name}'  — full CRUD (Company + Inspection + Notification)")
    print(f"    '{inspectors_group.name}' — view Company + full CRUD Inspection")

    return managers_group, inspectors_group


def clean_database():
    """Hard-delete all seeded data in safe dependency order."""
    print("\n  Cleaning database …")
    InspectionImage.objects.all().delete()
    CompanyImage.objects.all().delete()
    Inspection.objects.all().delete()
    Notification.objects.all().delete()
    Company.objects.all().delete()
    UserModel.objects.all().delete()
    Group.objects.all().delete()
    print("  Database wiped.")


# 5.  Main seeder

def seed():
    # 5-A  Clean
    clean_database()

    # 5-B  Groups
    managers_group, inspectors_group = setup_groups_and_permissions()

    # 5-C  Superuser
    print("\n👑  Creating superuser …")
    admin = UserModel(
        username=SUPERUSER["username"],
        email=SUPERUSER["email"],
        first_name=SUPERUSER["first_name"],
        last_name=SUPERUSER["last_name"],
        phone_number=SUPERUSER["phone_number"],
        user_id=SUPERUSER["user_id"],
        address=SUPERUSER["address"],
        is_staff=True,
        is_superuser=True,
        is_active=True,
    )
    admin.set_password(SHARED_PASSWORD)
    admin.save()
    print(f" Superuser: {admin.get_full_name()} ({admin.username})")

    # 5-D  Managers & their Inspector teams
    print("\n  Creating Managers and Inspector teams …")
    # manager_obj → [inspector_obj, …]
    team_map: dict = {}

    for entry in MANAGERS_WITH_TEAMS:
        mgr_data = entry["manager"]
        manager = _create_user(mgr_data, supervisor=admin, is_staff=True)
        manager.groups.add(managers_group)
        print(f" Manager: {manager.get_full_name()} ({manager.username})")

        team = []
        for insp_data in entry["inspectors"]:
            inspector = _create_user(insp_data, supervisor=manager, is_staff=True)
            inspector.groups.add(inspectors_group)
            team.append(inspector)
            print(f"Inspector: {inspector.get_full_name()} ({inspector.username})")

        team_map[manager] = team

    managers_list = list(team_map.keys())

    # 5-E  Companies
    print(f"\n  Creating {len(COMPANIES_DATA)} companies …")
    companies: list[Company] = []

    # Distribute companies across managers in a round-robin pattern so each
    # manager owns a balanced set, then pick an inspector from their own team.
    for idx, (name, activity, est_type, size_m2, workers) in enumerate(COMPANIES_DATA):
        manager = managers_list[idx % len(managers_list)]
        inspector = team_map[manager][idx % len(team_map[manager])]

        company_status = random.choice(ACTIVE_COMPANY_STATUSES)

        comp = Company.objects.create(
            company_name=name,
            company_number=f"CR-{100000 + idx:06d}",
            region=EGYPTIAN_REGIONS[idx % len(EGYPTIAN_REGIONS)],
            street_name=STREET_NAMES[idx % len(STREET_NAMES)],
            building_number=str(10 + idx * 3),
            activity_type=activity,
            electricity_meter_number=f"E-{20000 + idx:05d}",
            actual_workers_count=workers,
            establishment_type=est_type,
            size_description=f"مساحة تقريبية {size_m2} متر مربع، {workers} عامل.",
            status="active",
            manager=manager,
            assigned_to=inspector,
            status_by_inspector=company_status,
        )
        companies.append(comp)
        print(f" [{est_type}] {name} → مفتش: {inspector.get_full_name()}")

    # 5-F  Inspections
    print(f"\n Generating inspection reports …")
    inspections_created = 0

    for idx, comp in enumerate(companies):
        # ~75 % of companies have at least one inspection report
        if random.random() > 0.75:
            continue

        insp_status = _insp_status()

        insp = Inspection.objects.create(
            inspector=comp.assigned_to,
            company=comp,
            workers_size_estimation=(
                f"تقدير المفتش: يعمل بالموقع فعلياً حوالي "
                f"{comp.actual_workers_count} عامل."
            ),
            license_compliance=_compliance(),
            female_workers_element=_gender(),
            unlicensed_workers=_violation(),
            penalties_regulation=_regulation(),
            work_regulation=_regulation(),
            worker_file_maintenance=_violation(),
            extended_working_hours=_violation(),
            consecutive_shifts=_violation(),
            weekly_rest_schedule=_violation(),
            number_of_shifts=_shift(),
            inspector_opinion=INSPECTOR_OPINIONS[idx % len(INSPECTOR_OPINIONS)],
            mandoub_name_1="أحمد محمد السيد" if idx % 2 == 0 else "محمود علي عبدالله",
            mandoub_phone_1=f"0100{5000000 + idx:07d}",
            mandoub_name_2="",
            mandoub_phone_2="",
            status=insp_status,
        )
        inspections_created += 1

        # If approved → mark company as completed
        if insp_status == "approved":
            comp.status_by_inspector = "completed"
            comp.save(update_fields=["status_by_inspector"])

    print(f"{inspections_created} inspection reports created.")

    # 5-G  Notifications
    print(f"\n  Creating notifications …")
    notif_templates = [
        (
            "مهمة تفتيشية جديدة",
            "برجاء التوجه للفحص الميداني لمنشأة: {name} وإعداد تقرير تفصيلي خلال 48 ساعة.",
        ),
        (
            "تذكير بتقرير معلق",
            "لم يتم رفع تقرير التفتيش الخاص بمنشأة: {name}. برجاء إنهاء التقرير في أقرب وقت.",
        ),
        (
            "ملاحظة على تقرير مرفوع",
            "تم مراجعة تقرير منشأة: {name} وتوجد ملاحظات تحتاج تصحيحاً قبل اعتماده.",
        ),
    ]

    # Create one notification per company (sender = company's manager, recipient = company's inspector)
    for idx, comp in enumerate(companies):
        title, msg_tmpl = notif_templates[idx % len(notif_templates)]
        Notification.objects.create(
            recipient=comp.assigned_to,
            sender=comp.manager,
            title=title,
            message=msg_tmpl.format(name=comp.company_name),
            related_company=comp,   # ← enables direct deep-link from notification UI
            is_read=False,
        )

    print(f" {len(companies)} notifications created (one per company, related_company populated).")

    # 5-H  Summary 
    print("\n" + "=" * 60)
    print("  Seeding complete! Summary:")
    print(f"   • Superuser          : 1  ({SUPERUSER['username']})")
    print(f"   • Managers           : {len(managers_list)}")
    print(f"   • Inspectors         : {sum(len(t) for t in team_map.values())}")
    print(f"   • Companies          : {len(companies)}")
    print(f"   • Inspection reports : {inspections_created}")
    print(f"   • Notifications      : {len(companies)}")
    print(f"   • Shared password    : {SHARED_PASSWORD}")
    print("=" * 60)


# 6.  Entry point
if __name__ == "__main__":
    seed()