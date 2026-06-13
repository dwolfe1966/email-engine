#!/usr/bin/env python3
import argparse
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


FORBIDDEN_NAME_PATTERNS = [
    re.compile(r'openai api key', re.IGNORECASE),
    re.compile(r'sendgrid\.rtf$', re.IGNORECASE),
    re.compile(r'twilio.*recovery.*code', re.IGNORECASE),
    re.compile(r'milkbar_email_list.*subs.*\.csv$', re.IGNORECASE),
]

SECRET_PATTERNS = [
    ('sendgrid_api_key', re.compile(r'SG\.[A-Za-z0-9_-]{16,}\.[A-Za-z0-9_-]{16,}')),
    ('openai_api_key', re.compile(r'sk-[A-Za-z0-9_-]{20,}')),
    ('twilio_account_sid', re.compile(r'AC[a-fA-F0-9]{32}')),
    ('private_key_block', re.compile(r'-----BEGIN (?:RSA |EC |OPENSSH |)PRIVATE KEY-----')),
]

EMAIL_PATTERN = re.compile(r'\b[A-Za-z0-9._%+-]+@(?!example\.)[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b')

BINARY_SUFFIXES = {
    '.gif',
    '.ico',
    '.jpg',
    '.jpeg',
    '.pdf',
    '.png',
    '.woff',
    '.woff2',
}

DEFAULT_SKIP_PATTERNS = [
    re.compile(r'^tests/test_.*\.py$'),
]


@dataclass(frozen=True)
class Finding:
    path: str
    reason: str


def tracked_files() -> list[Path]:
    result = subprocess.run(
        ['git', 'ls-files'],
        check=True,
        capture_output=True,
        text=True,
    )
    return [Path(line) for line in result.stdout.splitlines() if line.strip()]


def is_binary_skipped(path: Path) -> bool:
    return path.suffix.lower() in BINARY_SUFFIXES


def forbidden_name_reason(path: Path) -> str | None:
    normalized = path.as_posix()
    for pattern in FORBIDDEN_NAME_PATTERNS:
        if pattern.search(normalized):
            return 'forbidden filename for local secret/PII artifact'
    return None


def scan_path(path: Path) -> list[Finding]:
    findings: list[Finding] = []
    name_reason = forbidden_name_reason(path)
    if name_reason:
        findings.append(Finding(path.as_posix(), name_reason))
    if not path.exists() or not path.is_file() or is_binary_skipped(path):
        return findings
    try:
        text = path.read_text(errors='ignore')
    except OSError as exc:
        findings.append(Finding(path.as_posix(), f'could not read file: {exc}'))
        return findings
    for reason, pattern in SECRET_PATTERNS:
        if pattern.search(text):
            findings.append(Finding(path.as_posix(), reason))
    if path.suffix.lower() == '.csv' and len(EMAIL_PATTERN.findall(text)) >= 5:
        findings.append(Finding(path.as_posix(), 'PII-like CSV with multiple real email addresses'))
    return findings


def scan(paths: list[Path]) -> list[Finding]:
    findings: list[Finding] = []
    for path in paths:
        findings.extend(scan_path(path))
    return findings


def default_scan_paths() -> list[Path]:
    paths = []
    for path in tracked_files():
        normalized = path.as_posix()
        if any(pattern.search(normalized) for pattern in DEFAULT_SKIP_PATTERNS):
            continue
        paths.append(path)
    return paths


def main() -> int:
    parser = argparse.ArgumentParser(
        description='Scan tracked or explicit files for high-confidence secret and PII artifacts.',
    )
    parser.add_argument('paths', nargs='*')
    args = parser.parse_args()

    paths = [Path(path) for path in args.paths] if args.paths else default_scan_paths()
    findings = scan(paths)
    if findings:
        for finding in findings:
            print(f'{finding.path}: {finding.reason}', file=sys.stderr)
        return 1
    print(f'No secret/PII guard findings across {len(paths)} file(s).')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
