#!/usr/bin/env python3
"""Audit and document every registered SchoolMind route.

The audit treats Flask's URL map as the runtime source of truth, while keeping a
release-contract endpoint set so an accidental route removal cannot silently
regenerate a smaller inventory. Source inspection supplies access decorators,
literal template names, and source locations. Runtime checks then verify guest
authentication boundaries and the English/Arabic HTML shell for every directly
renderable GET route.
"""
from __future__ import annotations

import ast
import inspect
import json
import os
import re
import sys
import tempfile
import textwrap
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

os.environ.setdefault("AUTO_INIT_DB", "true")
os.environ.setdefault("SEED_DEMO_DATA", "true")
os.environ.setdefault("SECRET_KEY", "route-audit-secret")

from schoolmind import create_app  # noqa: E402
from schoolmind.db import (  # noqa: E402
    ensure_platform_preferences,
    ensure_user_preferences,
    execute,
    query_all,
    query_one,
    utcnow,
)
from schoolmind.security import RATE_BUCKETS  # noqa: E402
from schoolmind.services.tokens import hash_token  # noqa: E402


# This is the shipped route contract, not the inventory implementation. New
# routes are automatically documented; removing one of these requires an
# intentional contract update in the same change.
REQUIRED_ENDPOINTS = frozenset(
    """
    api.billing_webhook
    api.export_students
    api.export_workspace_json
    api.health
    api.pulse
    api.readiness
    auth.accept_invite
    auth.forgot_password
    auth.google_callback
    auth.google_start
    auth.login
    auth.logout
    auth.reset_password
    auth.start
    dashboard.account_settings
    dashboard.activity_center
    dashboard.admin_backups
    dashboard.admin_billing
    dashboard.admin_consent
    dashboard.admin_create_user
    dashboard.admin_database
    dashboard.admin_home
    dashboard.admin_import
    dashboard.admin_invites
    dashboard.admin_operations
    dashboard.admin_outbox
    dashboard.admin_plan_limits
    dashboard.admin_queue_reset_link
    dashboard.admin_run_retention
    dashboard.admin_security
    dashboard.admin_settings
    dashboard.admin_toggle_user
    dashboard.admin_unlock_user
    dashboard.app_home
    dashboard.billing_checkout
    dashboard.billing_manual_activate
    dashboard.breathing_center
    dashboard.companion_studio
    dashboard.counselor_alert_action
    dashboard.counselor_create_plan
    dashboard.counselor_home
    dashboard.counselor_intervention
    dashboard.counselor_playbooks
    dashboard.counselor_student
    dashboard.daily_tips
    dashboard.games
    dashboard.help_center
    dashboard.journal_studio
    dashboard.mood_diary
    dashboard.nour_messages_api
    dashboard.onboarding
    dashboard.progress_hub
    dashboard.reports
    dashboard.resources
    dashboard.student_assessment
    dashboard.student_checkin
    dashboard.student_companion
    dashboard.student_goals
    dashboard.student_home
    dashboard.student_journal
    dashboard.student_support
    dashboard.support_plans
    dashboard.teacher_home
    dashboard.weekly_summary
    platform.platform_account_settings
    platform.platform_coupon_status
    platform.platform_coupons
    platform.platform_home
    platform.platform_login
    platform.platform_logout
    platform.platform_school
    platform.platform_school_status
    platform.platform_settings
    public.about
    public.accessibility
    public.compliance
    public.contact
    public.contact_sales
    public.cookies
    public.counselors
    public.data_processing_agreement
    public.data_retention
    public.demo
    public.faq
    public.features
    public.human_review
    public.humans_txt
    public.implementation
    public.incident_response
    public.index
    public.instant_experience
    public.llms_txt
    public.personalize_preferences
    public.pilot
    public.pricing
    public.privacy
    public.product
    public.public_preferences
    public.request_demo
    public.robots_txt
    public.safety
    public.schools
    public.security
    public.sitemap_xml
    public.student_data_notice
    public.students
    public.subprocessors
    public.teachers
    public.terms
    public.trial
    public.try_demo
    static
    """.split()
)

REQUIRED_ALIAS_RULES = {
    ("/ai-safety", "public.safety"),
    ("/safety", "public.safety"),
    ("/dpa", "public.data_processing_agreement"),
    ("/data-processing-agreement", "public.data_processing_agreement"),
}

METHOD_ORDER = {method: index for index, method in enumerate(("GET", "POST", "PUT", "PATCH", "DELETE"))}
LANGUAGE_SPECS = {
    "en": ('lang="en"', 'dir="ltr"'),
    "ar": ('lang="ar"', 'dir="rtl"'),
}
RAW_TRANSLATION_KEY_RE = re.compile(
    r"\b(?:auth|common|dashboard|errors|footer|forms|home|nav|platform|pricing|public|site)"
    r"\.[a-z0-9_.-]+\b"
)
NON_TRANSLATION_SUFFIXES = (
    ".css", ".html", ".js", ".json", ".md", ".png", ".py", ".pyc",
    ".svg", ".txt", ".webp", ".xml",
)


def visible_translation_keys(html: str) -> list[str]:
    """Return plausible rendered i18n keys without flagging visible filenames.

    The database-readiness screen intentionally shows release findings such as
    ``auth.cpython-314.pyc``. Those are filenames, not leaked translation keys.
    """
    return sorted(
        {
            match
            for match in RAW_TRANSLATION_KEY_RE.findall(html)
            if not match.endswith(NON_TRANSLATION_SUFFIXES) and "cpython-" not in match
        }
    )
SECTION_ORDER = (
    "Public routes",
    "Authentication routes",
    "Workspace-authenticated routes",
    "Platform routes",
)

JSON_ENDPOINTS = {
    "api.billing_webhook",
    "api.health",
    "api.pulse",
    "api.readiness",
    "dashboard.nour_messages_api",
}
TEXT_ENDPOINTS = {"public.humans_txt", "public.llms_txt", "public.robots_txt"}
DOWNLOAD_ENDPOINTS = {
    "api.export_students": "CSV download",
    "api.export_workspace_json": "JSON download",
}


@dataclass(frozen=True)
class SourceMetadata:
    decorators: tuple[str, ...]
    roles: tuple[str, ...]
    templates: tuple[str, ...]
    calls: frozenset[str]
    source: str


@dataclass
class RouteRecord:
    rule: str
    methods: tuple[str, ...]
    endpoint: str
    section: str
    classification: str
    surface: str
    templates: tuple[str, ...]
    guards: tuple[str, ...]
    source: str
    en_status: str = "N/A (non-HTML)"
    ar_status: str = "N/A (non-HTML)"

    def as_dict(self) -> dict[str, object]:
        return {
            "route": self.rule,
            "methods": list(self.methods),
            "classification": self.classification,
            "endpoint": self.endpoint,
            "surface": self.surface,
            "templates": list(self.templates),
            "guards": list(self.guards),
            "source": self.source,
            "i18n_audit": {"en": self.en_status, "ar": self.ar_status},
        }


def expression_name(node: ast.AST) -> str:
    if isinstance(node, ast.Call):
        return expression_name(node.func)
    if isinstance(node, ast.Attribute):
        return node.attr
    if isinstance(node, ast.Name):
        return node.id
    return ""


def source_metadata(view) -> SourceMetadata:
    original = inspect.unwrap(view)
    lines, start_line = inspect.getsourcelines(original)
    source_path = Path(inspect.getsourcefile(original) or "")
    parsed = ast.parse(textwrap.dedent("".join(lines)))
    function = next(
        node for node in parsed.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    )

    decorators = tuple(expression_name(node) for node in function.decorator_list)
    roles: list[str] = []
    for decorator in function.decorator_list:
        if isinstance(decorator, ast.Call) and expression_name(decorator) == "role_required":
            for argument in decorator.args:
                if isinstance(argument, ast.Constant) and isinstance(argument.value, str):
                    roles.append(argument.value)

    templates = sorted(
        {
            call.args[0].value
            for call in ast.walk(function)
            if isinstance(call, ast.Call)
            and expression_name(call) == "render_template"
            and call.args
            and isinstance(call.args[0], ast.Constant)
            and isinstance(call.args[0].value, str)
        }
    )
    calls = frozenset(
        expression_name(call)
        for call in ast.walk(function)
        if isinstance(call, ast.Call) and expression_name(call)
    )
    try:
        relative_source = source_path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        relative_source = source_path.as_posix()
    return SourceMetadata(
        decorators=decorators,
        roles=tuple(roles),
        templates=tuple(templates),
        calls=calls,
        source=f"{relative_source}:{start_line}",
    )


def access_details(endpoint: str, metadata: SourceMetadata | None) -> tuple[str, str]:
    namespace = endpoint.partition(".")[0]
    decorators = set(metadata.decorators if metadata else ())
    roles = metadata.roles if metadata else ()

    if endpoint == "static":
        return "Public routes", "Public asset"
    if namespace == "platform":
        if "platform_required" in decorators:
            return "Platform routes", "Platform authenticated"
        return "Platform routes", "Platform public/auth workflow"
    if roles:
        return "Workspace-authenticated routes", f"Authenticated workspace ({', '.join(roles)})"
    if "login_required" in decorators:
        return "Workspace-authenticated routes", "Authenticated workspace (any role)"
    if namespace == "auth":
        return "Authentication routes", "Authentication workflow (public)"
    if endpoint == "api.billing_webhook":
        return "Public routes", "Public webhook (HMAC authenticated)"
    if namespace == "api":
        return "Public routes", "Public API"
    return "Public routes", "Public"


def guard_details(endpoint: str, metadata: SourceMetadata | None) -> tuple[str, ...]:
    if endpoint == "static" or metadata is None:
        return ()
    guards: list[str] = []
    decorators = set(metadata.decorators)
    if metadata.roles:
        guards.append("role: " + "/".join(metadata.roles))
    elif "login_required" in decorators:
        guards.append("workspace session")
    if "platform_required" in decorators:
        guards.append("platform session")
    if "require_csrf" in decorators:
        guards.append("CSRF")
    if "rate_limit" in decorators:
        guards.append("rate limit")
    if endpoint == "api.billing_webhook":
        guards.append("HMAC signature")
    return tuple(guards)


def response_surface(endpoint: str, methods: tuple[str, ...], metadata: SourceMetadata | None) -> str:
    if endpoint == "static":
        return "Asset"
    if metadata and metadata.templates:
        return "HTML"
    if endpoint in DOWNLOAD_ENDPOINTS:
        return DOWNLOAD_ENDPOINTS[endpoint]
    if endpoint in JSON_ENDPOINTS:
        return "JSON"
    if endpoint in TEXT_ENDPOINTS:
        return "Plain text"
    if endpoint == "public.sitemap_xml":
        return "XML"
    if methods == ("POST",):
        return "Action/redirect"
    if metadata and "redirect" in metadata.calls:
        return "Redirect"
    return "Non-HTML"


def build_records(app) -> tuple[list[RouteRecord], dict[str, SourceMetadata]]:
    metadata_by_endpoint: dict[str, SourceMetadata] = {}
    for endpoint, view in app.view_functions.items():
        if endpoint != "static":
            metadata_by_endpoint[endpoint] = source_metadata(view)

    records: list[RouteRecord] = []
    for rule in sorted(app.url_map.iter_rules(), key=lambda item: (item.rule, item.endpoint)):
        methods = tuple(
            sorted(
                rule.methods - {"HEAD", "OPTIONS"},
                key=lambda method: (METHOD_ORDER.get(method, 99), method),
            )
        )
        metadata = metadata_by_endpoint.get(rule.endpoint)
        section, classification = access_details(rule.endpoint, metadata)
        templates = metadata.templates if metadata else ()
        records.append(
            RouteRecord(
                rule=rule.rule,
                methods=methods,
                endpoint=rule.endpoint,
                section=section,
                classification=classification,
                surface=response_surface(rule.endpoint, methods, metadata),
                templates=templates,
                guards=guard_details(rule.endpoint, metadata),
                source=metadata.source if metadata else "Flask built-in",
                en_status="N/A (no GET)" if templates and "GET" not in methods else "N/A (non-HTML)",
                ar_status="N/A (no GET)" if templates and "GET" not in methods else "N/A (non-HTML)",
            )
        )
    return records, metadata_by_endpoint


def prepare_samples(app) -> dict[str, object]:
    reset_token = "route-audit-reset-token"
    invite_token = "route-audit-invite-token"
    expires_at = (datetime.now(UTC) + timedelta(hours=2)).replace(microsecond=0).isoformat().replace("+00:00", "Z")

    with app.app_context():
        user_rows = query_all("SELECT id, school_id, role FROM users ORDER BY id")
        users = {row["role"]: row["id"] for row in user_rows}
        missing_roles = {"student", "teacher", "counselor", "admin"} - set(users)
        if missing_roles:
            raise AssertionError(f"Demo seed is missing route-audit roles: {sorted(missing_roles)}")
        school_id = query_one("SELECT id FROM schools WHERE slug = ?", ("pixel-academy",))["id"]
        platform_id = query_one("SELECT id FROM platform_admins ORDER BY id LIMIT 1")["id"]
        risk_event = query_one("SELECT id FROM risk_events WHERE school_id = ? ORDER BY id LIMIT 1", (school_id,))
        coupon = query_one("SELECT id FROM coupon_codes ORDER BY id LIMIT 1")

        for user_id in users.values():
            ensure_user_preferences(user_id)
        ensure_platform_preferences(platform_id)

        student_id = users["student"]
        execute(
            """
            INSERT INTO password_reset_tokens
            (school_id, user_id, email, token_hash, status, expires_at, created_at)
            VALUES (?, ?, ?, ?, 'pending', ?, ?)
            """,
            (
                school_id,
                student_id,
                "student@schoolmind.ai",
                hash_token(reset_token),
                expires_at,
                utcnow(),
            ),
        )
        execute(
            """
            INSERT INTO invite_tokens
            (school_id, email, role, group_name, token_hash, status, created_by, expires_at, created_at)
            VALUES (?, ?, 'student', ?, ?, 'pending', ?, ?, ?)
            """,
            (
                school_id,
                "route-audit-invite@example.test",
                "Route Audit",
                hash_token(invite_token),
                users["admin"],
                expires_at,
                utcnow(),
            ),
        )

    return {
        "users": users,
        "school_id": school_id,
        "platform_id": platform_id,
        "student_id": users["student"],
        "event_id": risk_event["id"] if risk_event else 1,
        "coupon_id": coupon["id"] if coupon else 1,
        "reset_token": reset_token,
        "invite_token": invite_token,
    }


VARIABLE_RE = re.compile(r"<(?:(?:[^:>]+):)?([^>]+)>")


def materialize_rule(record: RouteRecord, samples: dict[str, object]) -> str:
    def replacement(match: re.Match[str]) -> str:
        name = match.group(1)
        if name == "token":
            if record.endpoint == "auth.reset_password":
                return str(samples["reset_token"])
            return str(samples["invite_token"])
        values = {
            "role": "student",
            "user_id": samples["student_id"],
            "event_id": samples["event_id"],
            "school_id": samples["school_id"],
            "coupon_id": samples["coupon_id"],
            "plan": "starter",
            "filename": "css/pixel.css",
        }
        if name not in values:
            raise AssertionError(f"No route-audit sample for <{name}> in {record.rule}")
        return str(values[name])

    return VARIABLE_RE.sub(replacement, record.rule)


def auth_identity(metadata: SourceMetadata | None, samples: dict[str, object]) -> tuple[str, int] | None:
    if metadata is None:
        return None
    decorators = set(metadata.decorators)
    if "platform_required" in decorators:
        return "platform_admin_id", int(samples["platform_id"])
    if metadata.roles:
        return "user_id", int(samples["users"][metadata.roles[0]])
    if "login_required" in decorators:
        return "user_id", int(samples["users"]["admin"])
    return None


def set_identity_language(app, identity: tuple[str, int] | None, language: str) -> None:
    if identity is None:
        return
    key, identity_id = identity
    with app.app_context():
        if key == "platform_admin_id":
            execute("UPDATE platform_admin_preferences SET language = ? WHERE admin_id = ?", (language, identity_id))
        else:
            execute("UPDATE user_preferences SET language = ? WHERE user_id = ?", (language, identity_id))


def probe_html_routes(
    app,
    records: list[RouteRecord],
    metadata_by_endpoint: dict[str, SourceMetadata],
    samples: dict[str, object],
) -> list[str]:
    failures: list[str] = []
    for record in records:
        if not record.templates or "GET" not in record.methods:
            continue
        identity = auth_identity(metadata_by_endpoint.get(record.endpoint), samples)
        path = materialize_rule(record, samples)
        for language, markers in LANGUAGE_SPECS.items():
            set_identity_language(app, identity, language)
            client = app.test_client()
            with client.session_transaction() as session:
                session["language"] = language
                session["personalization_dismissed"] = True
                if identity:
                    session[identity[0]] = identity[1]
            try:
                response = client.get(path, follow_redirects=False)
            except Exception as exc:  # pragma: no cover - diagnostic path
                status = f"FAIL (raised {type(exc).__name__}: {exc})"
            else:
                html = response.get_data(as_text=True)
                missing_markers = [marker for marker in markers if marker not in html]
                raw_translation_keys = visible_translation_keys(html)
                if response.status_code != 200:
                    status = f"FAIL (HTTP {response.status_code})"
                elif response.mimetype != "text/html":
                    status = f"FAIL (MIME {response.mimetype})"
                elif missing_markers:
                    status = "FAIL (missing " + ", ".join(missing_markers) + ")"
                elif raw_translation_keys:
                    status = "FAIL (raw i18n keys: " + ", ".join(raw_translation_keys[:5]) + ")"
                else:
                    status = "PASS"
            if language == "en":
                record.en_status = status
            else:
                record.ar_status = status
            if status != "PASS":
                failures.append(f"{record.rule} [{language}] {status}")
    return failures


def probe_guest_boundaries(
    app,
    records: list[RouteRecord],
    metadata_by_endpoint: dict[str, SourceMetadata],
    samples: dict[str, object],
) -> tuple[int, list[str]]:
    checked = 0
    failures: list[str] = []
    for record in records:
        if "GET" not in record.methods:
            continue
        metadata = metadata_by_endpoint.get(record.endpoint)
        if metadata is None:
            continue
        decorators = set(metadata.decorators)
        is_platform = "platform_required" in decorators
        is_workspace = bool(metadata.roles) or "login_required" in decorators
        if not is_platform and not is_workspace:
            continue
        checked += 1
        response = app.test_client().get(materialize_rule(record, samples), follow_redirects=False)
        location = response.headers.get("Location", "")
        expected_login = "/platform/login" if is_platform else "/login"
        if response.status_code != 302 or expected_login not in location:
            failures.append(
                f"{record.rule} guest boundary returned {response.status_code} -> {location!r}; "
                f"expected redirect to {expected_login}"
            )
    return checked, failures


def validate_inventory(
    app,
    records: list[RouteRecord],
    metadata_by_endpoint: dict[str, SourceMetadata],
) -> list[str]:
    failures: list[str] = []
    endpoints = {record.endpoint for record in records}
    missing_endpoints = sorted(REQUIRED_ENDPOINTS - endpoints)
    if missing_endpoints:
        failures.append(f"Missing release-contract endpoints: {missing_endpoints}")

    registered_pairs = {(record.rule, record.endpoint) for record in records}
    missing_aliases = sorted(REQUIRED_ALIAS_RULES - registered_pairs)
    if missing_aliases:
        failures.append(f"Missing required alias rules: {missing_aliases}")

    for endpoint, metadata in metadata_by_endpoint.items():
        if "route" not in metadata.decorators:
            failures.append(f"{endpoint} has no discoverable @*.route decorator at {metadata.source}")
        for template in metadata.templates:
            template_path = ROOT / "schoolmind" / "templates" / template
            if not template_path.is_file():
                failures.append(f"{endpoint} references missing template {template}")

    map_endpoints = set(app.view_functions)
    if endpoints != map_endpoints:
        failures.append(
            "Route records and Flask view functions disagree: "
            f"records-only={sorted(endpoints - map_endpoints)}, views-only={sorted(map_endpoints - endpoints)}"
        )
    return failures


def markdown_inventory(records: list[RouteRecord], guest_boundaries: int) -> str:
    endpoint_count = len({record.endpoint for record in records})
    html_records = [record for record in records if record.templates and "GET" in record.methods]
    section_counts = Counter(record.section for record in records)
    lines = [
        "# Route Map",
        "",
        "Generated by `python scripts/route_audit.py`. Do not edit generated route rows by hand.",
        "",
        "## Audit summary",
        "",
        f"- Registered rules: **{len(records)}**",
        f"- Unique endpoints: **{endpoint_count}**",
        f"- Direct HTML GET rules verified in English and Arabic: **{len(html_records)}**",
        f"- Guest authentication boundaries verified: **{guest_boundaries}**",
        f"- Public rules: **{section_counts['Public routes']}**",
        f"- Authentication workflow rules: **{section_counts['Authentication routes']}**",
        f"- Workspace-authenticated rules: **{section_counts['Workspace-authenticated routes']}**",
        f"- Platform rules: **{section_counts['Platform routes']}**",
        "",
        "## Reading the inventory",
        "",
        "Each row lists route, methods, Flask endpoint, access classification, response surface, literal template(s), guards, source, and English/Arabic audit status. `PASS` means the route returned HTTP 200 HTML with the expected `<html lang>` and `dir` markers (`en`/LTR or `ar`/RTL). It verifies the bilingual shell and route renderability, not sentence-by-sentence translation completeness. `N/A` is used for redirects, APIs, downloads, assets, and action-only routes that do not directly render an HTML GET surface.",
        "",
        "The JSON companion at `docs/ROUTE_INVENTORY.json` contains the same records for tooling.",
    ]

    for section in SECTION_ORDER:
        lines.extend(["", f"## {section}", ""])
        for record in (item for item in records if item.section == section):
            methods = ",".join(record.methods)
            templates = ", ".join(f"`{template}`" for template in record.templates) or "none"
            guards = ", ".join(record.guards) or "none"
            lines.append(
                f"- `{record.rule}` - `{methods}` - `{record.endpoint}` - "
                f"access: **{record.classification}** - surface: {record.surface} - "
                f"template: {templates} - guards: {guards} - source: `{record.source}` - "
                f"EN: **{record.en_status}** - AR: **{record.ar_status}**"
            )
    return "\n".join(lines) + "\n"


def json_inventory(records: list[RouteRecord], guest_boundaries: int) -> str:
    payload = {
        "schema_version": 1,
        "generated_by": "scripts/route_audit.py",
        "summary": {
            "registered_rules": len(records),
            "unique_endpoints": len({record.endpoint for record in records}),
            "html_get_rules_verified_en_ar": sum(
                bool(record.templates and "GET" in record.methods) for record in records
            ),
            "guest_auth_boundaries_verified": guest_boundaries,
        },
        "routes": [record.as_dict() for record in records],
    }
    return json.dumps(payload, indent=2, ensure_ascii=False) + "\n"


def main() -> int:
    RATE_BUCKETS.clear()
    tmp = tempfile.NamedTemporaryFile(delete=False)
    tmp.close()
    try:
        app = create_app(
            {
                "TESTING": True,
                "DATABASE_PATH": tmp.name,
                "SECRET_KEY": "route-audit-secret",
                "ALLOW_SELF_REGISTER": True,
                "ENABLE_REQUEST_LOGGING": False,
            }
        )
        records, metadata_by_endpoint = build_records(app)
        failures = validate_inventory(app, records, metadata_by_endpoint)
        samples = prepare_samples(app)
        guest_boundaries, boundary_failures = probe_guest_boundaries(
            app, records, metadata_by_endpoint, samples
        )
        failures.extend(boundary_failures)
        failures.extend(probe_html_routes(app, records, metadata_by_endpoint, samples))
        if failures:
            raise SystemExit("Route audit failed:\n- " + "\n- ".join(failures))

        markdown_path = ROOT / "docs" / "ROUTE_MAP.md"
        json_path = ROOT / "docs" / "ROUTE_INVENTORY.json"
        markdown_path.write_text(markdown_inventory(records, guest_boundaries), encoding="utf-8")
        json_path.write_text(json_inventory(records, guest_boundaries), encoding="utf-8")
        print(
            "Route audit passed: "
            f"{len(records)} rules / {len({record.endpoint for record in records})} endpoints; "
            f"{sum(bool(record.templates and 'GET' in record.methods) for record in records)} "
            f"HTML rules checked in EN+AR; {guest_boundaries} guest boundaries checked."
        )
        return 0
    finally:
        try:
            os.unlink(tmp.name)
        except FileNotFoundError:
            pass


if __name__ == "__main__":
    raise SystemExit(main())
