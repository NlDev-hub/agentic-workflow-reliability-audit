#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

PRIVATE_PATTERNS = [
    'home directory path',
    'private workspace name',
    'private owner name',
    'private company identity',
    'internal approval queue label',
    'internal project lane label',
    'internal customer or prospect name',
]
RUNTIME_FORBIDDEN = [
    '<form', '<script', 'fetch(', 'xmlhttprequest', 'websocket', 'localstorage', 'sessionstorage',
    'indexeddb', 'stripe', 'paypal', 'checkout', 'upload', 'analytics', 'cookie', 'tracking',
]
CLAIM_PATTERNS = [
    r'\bcompliant\b', r'\bcompliance[- ]?ready\b', r'\baudit[- ]?ready\b', r'\bcertif(?:y|ied|ication)\b',
    r'\bregulator[- ]?ready\b', r'\bguarantee(?:d|s)?\b', r'\bguaranteed outcomes\b',
    r'\bsatisf(?:y|ies|ied)\b', r'\blegal advice\b', r'\btax advice\b', r'\bprocurement approved\b',
    r'\bsecurity assured\b', r'\breduces liability\b', r'\bROI\b', r'\bfully autonomous\b',
    r'\bpayment\b', r'\bpay\b', r'\binvoice\b', r'\bclient logs\b', r'\bcustomer data\b',
    r'\bmake[s]? .* safe\b', r'\bmake[s]? .* secure\b',
]
ALLOWED_CONTEXTS = [
    'no-data/no-payment',
    'no buyer, maintainer, platform, or payment signal',
    'there is no paid',
    'no payment',
    'no paid',
    'no money',
    'does not include payment',
    'stop before payment',
    'still blocked',
    'payment_flow',
    'external_action_scope',
    'no guaranteed outcomes',
    'does not guarantee roi',
    'not legal',
    'not approval to publish',
    'not a legal',
    'not a security',
    'not a compliance',
    'no claim that this audit makes',
    'not a request for paid work',
    'does not accept paid work',
    'does not accept paid work, payment',
    'does not accept paid work, payment, support requests',
    'separate private approval, payment, and legal boundary',
    'separate private approval',
    'not a request for paid work, support, a contract',
    'not a request for paid work, support, a contract, procurement, legal advice',
    'legal advice, security review, compliance certification, or guaranteed outcome',
    'legal advice, security review, compliance certification, or guaranteed outcomes',
]
REQUIRED_ISSUE_TEMPLATE_MARKERS = [
    'public feedback only',
    'do not include confidential',
    'client, customer, product, security, accounting, tender',
    'secrets, credentials, tokens, logs, private urls',
    'screenshots, attachments, account identifiers, personal data',
    'does not accept paid work, payment, support requests',
    'statements of work, contracts, invoices, procurement requests',
    'separate private approval, payment, and legal boundary',
]
FORBIDDEN_ISSUE_TEMPLATE_PROMPTS = [
    'email', 'phone', 'company name', 'budget', 'invoice address', 'billing',
    'upload a file', 'screenshot required', 'logs required', 'private url required',
]
REQUIRED_README_MARKERS = [
    'synthetic examples only',
    'no real customer, company, user, or product data',
    'no payment, invoice, refund, support, or money flow',
    'not legal, tax, compliance, procurement, security, certification, or regulatory advice',
    'no guaranteed outcomes',
    'validation question',
]
REQUIRED_FILES = [
    'README.md', 'sources.md', 'checklists/reliability-audit-checklist.md',
    'examples/synthetic-audit-report.md', 'examples/evidence-bundle-template.md',
    'docs/index.html', '.github/workflows/validate.yml',
]


def result(ok: bool, errors: list[str], **extra: Any) -> dict[str, Any]:
    payload = {'ok': ok, 'errors': errors}
    payload.update(extra)
    return payload


def is_allowed_claim_context(text: str, start: int, end: int) -> bool:
    window = text[max(0, start - 100): min(len(text), end + 100)]
    return any(marker in window for marker in ALLOWED_CONTEXTS)


def scan_text_for_risky_claims(rel: str, text: str) -> list[str]:
    errors: list[str] = []
    lower = text.lower()
    for pattern in CLAIM_PATTERNS:
        for match in re.finditer(pattern, lower, re.IGNORECASE):
            if not is_allowed_claim_context(lower, match.start(), match.end()):
                errors.append(f'{rel} contains risky claim wording: {match.group(0)}')
    return errors


def scan_publishable_files(root: Path) -> list[str]:
    errors: list[str] = []
    skipped = {'scripts/validate_public_package.py', 'tests/test_public_package.py'}
    for path in root.rglob('*'):
        if not path.is_file() or '.git' in path.parts or '__pycache__' in path.parts or '.pytest_cache' in path.parts:
            continue
        rel = str(path.relative_to(root))
        if rel in skipped:
            continue
        data = path.read_bytes()
        lower_bytes = data.lower()
        for marker in PRIVATE_PATTERNS:
            if marker.encode() in lower_bytes:
                errors.append(f'{rel} contains private placeholder marker: {marker}')
        if path.suffix.lower() not in {'.md', '.py', '.json', '.yml', '.yaml', '.txt', '.html'}:
            continue
        text = data.decode('utf-8', errors='replace').lower()
        errors.extend(scan_text_for_risky_claims(rel, text))
    return errors


def validate_package(root: Path = ROOT) -> dict[str, Any]:
    errors: list[str] = []
    for rel in REQUIRED_FILES:
        if not (root / rel).exists():
            errors.append(f'missing required file: {rel}')
    readme = root / 'README.md'
    if readme.exists():
        text = readme.read_text(encoding='utf-8').lower()
        for marker in REQUIRED_README_MARKERS:
            if marker not in text:
                errors.append(f'README missing marker: {marker}')
    workflow = root / '.github' / 'workflows' / 'validate.yml'
    if workflow.exists():
        workflow_text = workflow.read_text(encoding='utf-8').lower()
        for marker in ('contents: read', 'persist-credentials: false', 'scripts/validate_public_package.py', 'unittest discover'):
            if marker not in workflow_text:
                errors.append(f'workflow missing least-privilege/test marker: {marker}')
        if 'pull_request_target' in workflow_text:
            errors.append('workflow must not use pull_request_target')
    docs = root / 'docs' / 'index.html'
    if docs.exists():
        text = docs.read_text(encoding='utf-8').lower()
        for token in RUNTIME_FORBIDDEN:
            if token in text:
                errors.append(f'docs/index.html contains runtime/payment/data token: {token}')
        for marker in ('synthetic examples only', 'no real customer, company, user, or product data', 'no payment', 'no guaranteed outcomes'):
            if marker not in text:
                errors.append(f'docs/index.html missing marker: {marker}')
    issue_template = root / '.github' / 'ISSUE_TEMPLATE' / 'public-fit-check.yml'
    if issue_template.exists():
        template_text = issue_template.read_text(encoding='utf-8').lower()
        for marker in REQUIRED_ISSUE_TEMPLATE_MARKERS:
            if marker not in template_text:
                errors.append(f'public-fit-check issue template missing boundary marker: {marker}')
        for forbidden in FORBIDDEN_ISSUE_TEMPLATE_PROMPTS:
            if forbidden in template_text:
                errors.append(f'public-fit-check issue template asks for unsafe intake prompt: {forbidden}')
    errors.extend(scan_publishable_files(root))
    summary = {
        'package': 'agentic-workflow-reliability-audit',
        'external_action_authorized': True,
        'external_action_scope': 'Niko/NlDev-hub public proof repo/page only; no outreach, payment, legal, platform terms, wallet, or real-data action',
        'payment_flow': False,
        'real_data_used': False,
        'owner_company_identity_used': False,
        'unsupported_claims': False,
        'public_signal_target': 'stars, forks, issues, pull requests, clone/view traffic, or concrete checklist/report suggestions',
        'true_paid_reputable_outcomes': 0,
    }
    out = root / 'sample-output' / 'package-summary.json'
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(summary, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    return result(not errors, errors, summary=summary)


def main() -> int:
    payload = validate_package(ROOT)
    if not payload['ok']:
        print('FAIL: public package validation failed')
        for error in payload['errors']:
            print(f'- {error}')
        return 1
    print('PASS: public package validation passed')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
