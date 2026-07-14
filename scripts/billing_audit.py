from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from schoolmind.config import PLANS
from schoolmind.services.billing import annual_effective_monthly, annual_savings, pricing_catalog


def fail(message):
    raise AssertionError(message)


def main():
    standard = PLANS.get("starter")
    pro = PLANS.get("growth")
    custom = PLANS.get("scale")
    if not standard or standard["price"] != 9.99 or standard["six_month_price"] != 49.99 or standard["annual_price"] != 89.99 or standard["student_limit"] != 300:
        fail("Standard plan must be $9.99/month, $49.99/6 months, and $89.99/year with a 300-student included limit.")
    if not pro or pro["price"] != 49 or pro["six_month_price"] != 249 or pro["annual_price"] != 399 or pro["student_limit"] != 1000:
        fail("Pro plan must be $49/month, $249/6 months, and $399/year with a 1,000-student included limit.")
    if not custom or custom["price"] != 0:
        fail("Custom plan must not present a fake fixed monthly price.")
    if annual_savings("starter") <= 0 or annual_savings("growth") <= 0:
        fail("Annual billing must show a real saving against monthly billing.")
    if annual_effective_monthly("starter") >= standard["price"]:
        fail("Standard annual effective monthly price must be lower than monthly.")
    if annual_effective_monthly("growth") >= pro["price"]:
        fail("Pro annual effective monthly price must be lower than monthly.")
    catalog = pricing_catalog()
    if len(catalog) != 3:
        fail("Pricing catalog must expose exactly the three owner-approved plan lanes.")
    pricing = (ROOT / "schoolmind/templates/public/pricing.html").read_text(encoding="utf-8")
    required = [
        "public.pricing.trust_trial",
        "public.pricing.start_monthly",
        "public.pricing.start_six_month",
        "public.pricing.start_annual",
        "public.pricing.comparison_eyebrow",
        "public.pricing.after_heading",
        "public.pricing.extra_seats",
        "public.pricing.guardrails_heading",
        "public.pricing.after_point_2",
    ]
    for needle in required:
        if needle not in pricing:
            fail(f"Pricing page missing required billing copy: {needle}")
    start = (ROOT / "schoolmind/templates/auth/start.html").read_text(encoding="utf-8")
    if "auth.start.billing_label" not in start or "billing_cycle" not in start:
        fail("Trial signup must capture intended post-trial billing cycle.")
    billing = (ROOT / "schoolmind/templates/dashboard/billing.html").read_text(encoding="utf-8")
    for needle in ["dashboard.billing.checkout_monthly", "dashboard.billing.checkout_six", "dashboard.billing.checkout_annual", "dashboard.billing.provider_required", "dashboard.billing.manual_locked"]:
        if needle not in billing:
            fail(f"Dashboard billing page missing: {needle}")
    service = (ROOT / "schoolmind/services/billing.py").read_text(encoding="utf-8")
    for needle in ["CHECKOUT_{plan_key}_{cycle.upper()}_URL", "normalize_billing_cycle", "pricing_catalog"]:
        if needle not in service:
            fail(f"Billing service missing: {needle}")
    print("Billing audit passed: monthly, six-month, and annual pricing, checkout guardrails, and trial boundaries verified.")


if __name__ == "__main__":
    main()
