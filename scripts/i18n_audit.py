"""Audit bilingual public-site readiness for SchoolMind AI."""
from __future__ import annotations

import os
import re
import sys
import tempfile
from pathlib import Path

os.environ.setdefault("AUTO_INIT_DB", "true")
os.environ.setdefault("SEED_DEMO_DATA", "true")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from schoolmind import create_app  # noqa: E402
from schoolmind.i18n import TRANSLATIONS  # noqa: E402

LITERAL_TRANSLATION_CALL = re.compile(r'''(?<![A-Za-z0-9_])t\(\s*(["'])([^"']+)\1\s*\)''')
REQUIRED_TEMPLATE_MARKERS = [
    "t('home.hero.line_one')",
    "t('home.hero.line_two')",
    "t('home.features.title')",
    "t('home.roles.title')",
    "t('home.security.title')",
    "t('home.pricing.title')",
    "t('home.final.title_new')",
]

PUBLIC_LOCALIZED_ROUTES = {
    "/accessibility": ("Accessibility is part of product quality", "إمكانية الوصول جزء من جودة المنتج"),
    "/compliance": ("Compliance cannot be claimed casually", "لا يجوز الادعاء بالامتثال دون أساس"),
    "/cookies": ("Minimal cookies for a safer school product", "أقل قدر من ملفات تعريف الارتباط"),
    "/counselors": ("A supervised support hub", "مركز دعم خاضع للإشراف"),
    "/data-processing-agreement": ("A school data product needs a data processing agreement", "يحتاج منتج بيانات مدرسي إلى اتفاقية معالجة بيانات"),
    "/dpa": ("A school data product needs a data processing agreement", "يحتاج منتج بيانات مدرسي إلى اتفاقية معالجة بيانات"),
    "/data-retention": ("Student support data should not live forever", "لا ينبغي أن تبقى بيانات دعم الطلاب"),
    "/demo": ("Enter SchoolMind AI immediately", "ادخل SchoolMind AI فورًا"),
    "/human-review": ("School staff stay responsible", "يبقى موظفو المدرسة مسؤولين"),
    "/implementation": ("Launch carefully", "أطلق بعناية"),
    "/incident-response": ("Security incidents need a written workflow", "تحتاج الحوادث الأمنية إلى سير عمل مكتوب"),
    "/pilot": ("Use a controlled pilot", "استخدم تجربة مضبوطة"),
    "/product": ("One supervised operating system", "نظام تشغيل واحد خاضع للإشراف"),
    "/features": ("Feature depth that supports", "مزايا متعمقة تدعم"),
    "/pricing": ("Clear school pricing", "تسعير واضح للمدارس"),
    "/schools": ("A safer operating layer", "طبقة تشغيل أكثر أمانًا"),
    "/security": ("Built around school trust", "مصمم حول ثقة المدرسة"),
    "/privacy": ("Student data needs governance", "بيانات الطلاب تحتاج إلى حوكمة"),
    "/contact": ("Request a demo, pilot", "اطلب مناقشة عرض"),
    "/about": ("A global school support platform", "منصة عالمية لدعم المدارس"),
    "/trial": ("Start with a 30-day trial", "ابدأ بتجربة لمدة 30 يومًا"),
    "/request-demo": ("For schools that need a serious walkthrough", "للمدارس التي تحتاج إلى جولة جادة"),
    "/ai-safety": ("AI-assisted does not mean AI-controlled", "المساعدة بالذكاء الاصطناعي لا تعني تحكمه"),
    "/safety": ("AI-assisted does not mean AI-controlled", "المساعدة بالذكاء الاصطناعي لا تعني تحكمه"),
    "/student-data-notice": ("Students and guardians deserve plain language", "يستحق الطلاب وأولياء الأمور لغة واضحة"),
    "/students": ("A calm student space", "مساحة هادئة للطالب"),
    "/subprocessors": ("External services must be listed", "يجب إدراج الخدمات الخارجية"),
    "/teachers": ("Classroom pulse without making teachers responsible", "نبض الصف دون تحميل المعلمين"),
    "/terms": ("Use SchoolMind AI as a supervised school support platform", "استخدم SchoolMind AI كمنصة دعم مدرسي"),
    "/faq": ("Hard questions schools should ask", "أسئلة مهمة ينبغي للمدارس طرحها"),
}


def main() -> int:
    used_template_keys: set[str] = set()
    for template_path in (ROOT / "schoolmind" / "templates").rglob("*.html"):
        template_source = template_path.read_text(encoding="utf-8")
        used_template_keys.update(
            match.group(2) for match in LITERAL_TRANSLATION_CALL.finditer(template_source)
        )
    for language in ("en", "ar"):
        missing_keys = sorted(used_template_keys - set(TRANSLATIONS[language]))
        if missing_keys:
            preview = ", ".join(missing_keys[:20])
            suffix = " ..." if len(missing_keys) > 20 else ""
            raise SystemExit(
                f"{language.upper()} dictionary is missing {len(missing_keys)} literal template keys: "
                f"{preview}{suffix}"
            )

    index_template = (ROOT / "schoolmind" / "templates" / "public" / "index.html").read_text(encoding="utf-8")
    base_template = (ROOT / "schoolmind" / "templates" / "base.html").read_text(encoding="utf-8")
    missing = [marker for marker in REQUIRED_TEMPLATE_MARKERS if marker not in index_template]
    if missing:
        raise SystemExit(f"Missing translated homepage markers: {missing}")
    if "language-control" not in base_template or "language_url('ar')" not in base_template or "language_url('en')" not in base_template:
        raise SystemExit("Base template is missing its single persistent language control.")

    tmp = tempfile.NamedTemporaryFile(delete=False)
    tmp.close()
    try:
        app = create_app({"TESTING": True, "DATABASE_PATH": tmp.name, "SECRET_KEY": "test-secret", "ALLOW_SELF_REGISTER": True})
        client = app.test_client()
        en = client.get("/")
        ar = client.get("/?language=ar")
        if en.status_code != 200 or ar.status_code != 200:
            raise SystemExit("Public homepage did not load in both languages.")
        en_html = en.data.decode("utf-8")
        ar_html = ar.data.decode("utf-8")
        if 'lang="en"' not in en_html or 'dir="ltr"' not in en_html:
            raise SystemExit("English homepage is not marked LTR correctly.")
        if 'lang="ar"' not in ar_html or 'dir="rtl"' not in ar_html:
            raise SystemExit("Arabic homepage is not marked RTL correctly.")
        for needle in ["مدارس أذكى", "دعم أقوى", "الخصوصية. الأمان. الثقة.", "القياسية", "الاحترافية"]:
            if needle not in ar_html:
                raise SystemExit(f"Arabic homepage missing translated copy: {needle}")
        for needle in ["Smarter Schools.", "Stronger Support.", "Privacy. Security. Trust.", "$9.99", "$399"]:
            if needle not in en_html:
                raise SystemExit(f"English homepage missing approved copy: {needle}")
        for raw_key in ["home.", "nav.", "footer."]:
            if raw_key in en_html or raw_key in ar_html:
                raise SystemExit(f"Rendered homepage exposed raw translation key: {raw_key}")
        if ar_html.count('class="language-control"') != 1:
            raise SystemExit("Public header must render exactly one language control.")

        for path, (english_marker, arabic_marker) in PUBLIC_LOCALIZED_ROUTES.items():
            en_page = client.get(f"{path}?language=en")
            ar_page = client.get(f"{path}?language=ar")
            if en_page.status_code != 200 or ar_page.status_code != 200:
                raise SystemExit(f"Localized public route failed to load: {path}")
            en_page_html = en_page.data.decode("utf-8")
            ar_page_html = ar_page.data.decode("utf-8")
            if english_marker not in en_page_html:
                raise SystemExit(f"English public route missing localized copy: {path}")
            if arabic_marker not in ar_page_html:
                raise SystemExit(f"Arabic public route missing localized copy: {path}")
            if 'lang="en"' not in en_page_html or 'dir="ltr"' not in en_page_html:
                raise SystemExit(f"English public route is not marked LTR: {path}")
            if 'lang="ar"' not in ar_page_html or 'dir="rtl"' not in ar_page_html:
                raise SystemExit(f"Arabic public route is not marked RTL: {path}")
            if "public." in en_page_html or "public." in ar_page_html:
                raise SystemExit(f"Rendered public route exposed a raw translation key: {path}")
            if path in {"/pricing", "/trial", "/request-demo"}:
                for price in ("$9.99", "$49"):
                    if price not in en_page_html or price not in ar_page_html:
                        raise SystemExit(f"Localized pricing route changed an approved price ({price}): {path}")

        persisted_ar = client.get("/product")
        if 'lang="ar"' not in persisted_ar.data.decode("utf-8"):
            raise SystemExit("Arabic language choice did not persist across public routes.")
    finally:
        try:
            os.unlink(tmp.name)
        except FileNotFoundError:
            pass
    print(
        f"I18n audit passed: {len(used_template_keys)} literal template keys + homepage + "
        f"{len(PUBLIC_LOCALIZED_ROUTES)} public routes"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
