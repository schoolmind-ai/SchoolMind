#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Human-readable release claims mapped to their localized template keys. This
# keeps the audit meaningful after moving visible copy such as "Delivery health"
# into the shared EN/AR catalog.
OUTBOX_LOCALIZED_MARKERS = {
    "Delivery health": "dashboard.outbox.delivery_health",
    "Queue test email": "dashboard.outbox.test_email",
    "Attempts": "dashboard.outbox.attempts",
    "Production queue warning": "dashboard.outbox.queue_note",
}

REQUIRED = {
    "schoolmind/services/mailer.py": [
        "email_delivery_health",
        "queue_template_email",
        "queue_test_email",
        "EMAIL_DELIVERY_MODE=queue stores messages only",
        "attempt_count",
        "last_error",
    ],
    "schoolmind/services/email_templates.py": [
        "workspace_invite",
        "password_reset",
        "sales_lead_notification",
        "trial_started",
        "test_email",
        "required_transactional_templates",
    ],
    "schoolmind/templates/dashboard/outbox.html": list(OUTBOX_LOCALIZED_MARKERS.values()),
    "schoolmind/db.py": [
        "message_type TEXT NOT NULL DEFAULT 'transactional'",
        "attempt_count INTEGER NOT NULL DEFAULT 0",
        "last_error TEXT NOT NULL DEFAULT ''",
        "last_attempt_at TEXT",
        "idx_outbox_type_status",
    ],
    ".env.example": [
        "EMAIL_DELIVERY_MODE=queue",
        "SMTP_HOST=",
        "SMTP_FROM=support@schoolmind.ai",
        "TEST_EMAIL_RECIPIENT=support@schoolmind.ai",
    ],
    "docs/phases/PHASE_13_EMAIL_NOTIFICATIONS.md": [
        "Phase 13",
        "Email delivery is not fake",
        "SMTP",
        "queue-only",
    ],
}


def main():
    for rel, markers in REQUIRED.items():
        path = ROOT / rel
        if not path.exists():
            raise SystemExit(f"Missing required file: {rel}")
        text = path.read_text(encoding="utf-8")
        for marker in markers:
            if marker not in text:
                raise SystemExit(f"{rel} missing marker: {marker}")
    print("Email readiness audit passed")


if __name__ == "__main__":
    main()
