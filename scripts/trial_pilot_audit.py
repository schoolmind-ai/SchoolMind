#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
checks = {
    "schoolmind/templates/public/trial.html": [
        "public.trial.eyebrow",
        "public.trial.path_heading",
        "public.common.start_standard_trial",
        "public.common.request_guided_pilot",
        "public.trial.free_title",
    ],
    "schoolmind/templates/public/pilot.html": [
        "public.pilot.heading",
        "lead_type",
        "guided_pilot",
        "privacy_review_needed",
        "student_count",
    ],
    "schoolmind/templates/public/request_demo.html": [
        "lead_type",
        "student_count",
        "preferred_path",
        "requested_plan",
        "billing_cycle",
    ],
    "schoolmind/templates/auth/start.html": [
        "accept_human_review",
        "accept_trial_boundary",
        "auth.start.guided_title",
        "auth.start.self_serve_title",
    ],
    "schoolmind/public.py": [
        "def trial()",
        "normalize_sales_lead",
        "queue_sales_lead_notification",
        "privacy_review_needed",
    ],
    "schoolmind/db.py": [
        "lead_type TEXT NOT NULL DEFAULT 'contact'",
        "student_count INTEGER NOT NULL DEFAULT 0",
        "idx_leads_type_status",
    ],
}

missing = []
for rel, needles in checks.items():
    text = (ROOT / rel).read_text(encoding="utf-8")
    for needle in needles:
        if needle not in text:
            missing.append(f"{rel}: missing {needle}")

if missing:
    raise SystemExit("\n".join(missing))

print("Trial/pilot audit passed")
