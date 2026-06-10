#!/usr/bin/env python3
import argparse
import json
import mailbox
import os
import sys
import time
from datetime import datetime, timezone
from email.message import Message
from pathlib import Path
from typing import Any


def message_text(message: Message, limit: int) -> str:
    if message.is_multipart():
        parts = []
        for part in message.walk():
            if part.is_multipart():
                continue
            content_type = part.get_content_type()
            if content_type not in {'text/plain', 'message/delivery-status'}:
                continue
            try:
                parts.append(part.get_content())
            except Exception:
                payload = part.get_payload(decode=True) or b''
                parts.append(payload.decode('utf-8', errors='replace'))
        text = '\n'.join(str(part) for part in parts)
    else:
        try:
            text = str(message.get_content())
        except Exception:
            payload = message.get_payload(decode=True) or b''
            text = payload.decode('utf-8', errors='replace')
    return text.strip().replace('\x00', '')[:limit]


def message_received_at(message: Message) -> str | None:
    date_header = message.get('Date')
    if date_header:
        return date_header
    return None


def summarize_quarantine_message(key: str, message: Message, *, preview_chars: int = 240) -> dict[str, Any]:
    return {
        'key': key,
        'from': message.get('From'),
        'to': message.get('To'),
        'subject': message.get('Subject'),
        'date': message_received_at(message),
        'quarantine_reason': message.get('X-Email-Engine-Quarantine-Reason'),
        'content_type': message.get_content_type(),
        'preview': message_text(message, preview_chars),
    }


def load_maildir(path: str) -> mailbox.Maildir:
    candidate = Path(path)
    if not candidate.exists():
        raise FileNotFoundError(f'Quarantine Maildir does not exist: {path}')
    return mailbox.Maildir(candidate, create=False)


def list_quarantine(path: str, *, limit: int, preview_chars: int) -> list[dict[str, Any]]:
    maildir = load_maildir(path)
    rows: list[dict[str, Any]] = []
    for key in sorted(maildir.keys())[:limit]:
        rows.append(summarize_quarantine_message(key, maildir[key], preview_chars=preview_chars))
    return rows


def message_age_hours(maildir: mailbox.Maildir, key: str, now: float | None = None) -> float:
    now = now if now is not None else time.time()
    path_info = maildir._lookup(key)  # noqa: SLF001 - stdlib Maildir exposes no public path lookup.
    message_path = Path(path_info)
    if not message_path.is_absolute():
        message_path = Path(maildir._path) / message_path  # noqa: SLF001 - stdlib Maildir path.
    return max(0.0, (now - message_path.stat().st_mtime) / 3600)


def quarantine_stats(
    path: str,
    *,
    warning_count: int,
    critical_count: int,
    max_age_hours: float,
) -> dict[str, Any]:
    maildir = load_maildir(path)
    keys = sorted(maildir.keys())
    now = time.time()
    ages = [message_age_hours(maildir, key, now) for key in keys]
    oldest_age_hours = max(ages) if ages else 0.0
    stale_count = sum(1 for age in ages if age >= max_age_hours)
    status = 'ok'
    reasons: list[str] = []
    if len(keys) >= critical_count:
        status = 'critical'
        reasons.append(f'quarantine count {len(keys)} >= critical threshold {critical_count}')
    elif len(keys) >= warning_count:
        status = 'warning'
        reasons.append(f'quarantine count {len(keys)} >= warning threshold {warning_count}')
    if stale_count:
        status = 'critical' if status == 'critical' else 'warning'
        reasons.append(f'{stale_count} message(s) older than {max_age_hours:g} hour(s)')
    return {
        'status': status,
        'message_count': len(keys),
        'warning_count': warning_count,
        'critical_count': critical_count,
        'max_age_hours': max_age_hours,
        'oldest_age_hours': round(oldest_age_hours, 2),
        'stale_count': stale_count,
        'reasons': reasons,
        'checked_at': datetime.now(timezone.utc).isoformat(),
    }


def purge_quarantine(
    path: str,
    *,
    keys: list[str],
    older_than_days: int | None,
    all_messages: bool,
    dry_run: bool,
) -> dict[str, Any]:
    maildir = load_maildir(path)
    selected = set(keys)
    max_age_hours = older_than_days * 24 if older_than_days is not None else None
    removed: list[str] = []
    skipped: list[str] = []
    for key in sorted(maildir.keys()):
        remove = all_messages or key in selected
        if max_age_hours is not None:
            remove = remove or message_age_hours(maildir, key) > max_age_hours
        if not remove:
            skipped.append(key)
            continue
        removed.append(key)
        if not dry_run:
            maildir.remove(key)
    if not dry_run:
        maildir.flush()
    return {
        'removed_count': len(removed),
        'skipped_count': len(skipped),
        'removed_keys': removed,
        'dry_run': dry_run,
        'purged_at': datetime.now(timezone.utc).isoformat(),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description='Inspect or purge managed-SMTP DSN quarantine Maildir messages.',
    )
    parser.add_argument('path', nargs='?', default=os.environ.get('MANAGED_SMTP_DSN_QUARANTINE'))
    parser.add_argument('--json', action='store_true')
    parser.add_argument('--limit', type=int, default=50)
    parser.add_argument('--preview-chars', type=int, default=240)
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--warning-count', type=int, default=5)
    parser.add_argument('--critical-count', type=int, default=25)
    parser.add_argument('--max-age-hours', type=float, default=24)
    parser.add_argument('--purge-key', action='append', default=[])
    parser.add_argument('--purge-older-than-days', type=int)
    parser.add_argument('--purge-all', action='store_true')
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()

    if not args.path:
        print('Quarantine Maildir path is required or MANAGED_SMTP_DSN_QUARANTINE must be set', file=sys.stderr)
        return 2

    try:
        if args.check:
            result = quarantine_stats(
                args.path,
                warning_count=args.warning_count,
                critical_count=args.critical_count,
                max_age_hours=args.max_age_hours,
            )
            print(json.dumps(result, indent=2))
            if result['status'] == 'critical':
                return 2
            if result['status'] == 'warning':
                return 1
            return 0
        if args.purge_key or args.purge_older_than_days is not None or args.purge_all:
            result = purge_quarantine(
                args.path,
                keys=args.purge_key,
                older_than_days=args.purge_older_than_days,
                all_messages=args.purge_all,
                dry_run=args.dry_run,
            )
            print(json.dumps(result, indent=2))
            return 0
        rows = list_quarantine(args.path, limit=args.limit, preview_chars=args.preview_chars)
    except FileNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps({'items': rows, 'total': len(rows), 'limit': args.limit}, indent=2))
        return 0

    if not rows:
        print('No quarantined DSN mailbox messages found.')
        return 0
    for row in rows:
        print(f"{row['key']} | {row.get('subject') or '(no subject)'} | {row.get('from') or '-'}")
        print(f"  reason: {row.get('quarantine_reason') or '-'}")
        print(f"  preview: {row.get('preview') or '-'}")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
