#!/usr/bin/env python3
"""
vCard2text — Convert vCard (.vcf) files to readable text.
Supports vCard 2.1, 3.0, and 4.0.
"""

__version__ = '2.0'

import sys
import re
import glob
from datetime import datetime
from pathlib import Path
import quopri


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# All known vCard property names across versions 2.1, 3.0, 4.0.
# Anything outside this set is treated as a custom/vendor field.
STANDARD_FIELDS = {
    'FN', 'N', 'TEL', 'EMAIL', 'ADR', 'ADDR', 'ORG', 'TITLE', 'NOTE', 'BDAY',
    'LABEL', 'URL', 'NICKNAME', 'ANNIVERSARY', 'GENDER', 'CATEGORIES',
    'CREATED', 'REVISED', 'VERSION', 'BEGIN', 'END', 'REV', 'PHOTO', 'SOUND',
    'KEY', 'LOGO', 'AGENT', 'PRODID', 'PROFILE', 'SOURCE', 'NAME', 'CLASS',
    'SORT-STRING', 'UID', 'MAILER', 'TZ', 'GEO', 'ROLE', 'MEMBER', 'RELATED',
    'LANG', 'IMPP', 'XML', 'CLIENTPIDMAP', 'CALADRURI', 'CALURI', 'FBURL',
    'EXPERTISE', 'HOBBY', 'INTEREST', 'ORG-DIRECTORY',
}

# Binary or internal fields — silently ignored, never shown as custom.
SILENT_FIELDS = {
    'VERSION', 'BEGIN', 'END', 'PHOTO', 'SOUND', 'KEY', 'LOGO',
    'AGENT', 'PRODID', 'PROFILE', 'SOURCE', 'NAME', 'CLASS',
}

MONTHS = [
    'January', 'February', 'March', 'April', 'May', 'June',
    'July', 'August', 'September', 'October', 'November', 'December',
]

DIVIDER     = '─' * 60
DIVIDER_HVY = '=' * 60
DIVIDER_CTX = '-' * 60

# Fields that produce visible output. Used to decide if a contact
# has any useful content worth writing to the output file.
DISPLAYABLE_FIELDS = {
    'name', 'phones', 'emails', 'addresses', 'organizations',
    'title', 'urls', 'notes', 'birthday', 'nickname', 'label',
    'anniversary', 'gender', 'categories', 'created', 'revised',
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def strip_uri_prefix(value):
    """Remove tel: or mailto: URI prefixes (case-insensitive)."""
    low = value.lower()
    if low.startswith('tel:'):
        return value[4:]
    if low.startswith('mailto:'):
        return value[7:]
    return value


def extract_type(key_part):
    """
    Return the TYPE label for a field (e.g. 'Work/Voice', 'Home').
    Handles v3.0+ TYPE=WORK,VOICE and v2.1 inline TEL;WORK;VOICE.
    Always Title Case.
    """
    match = re.search(r'TYPE=([^;:]+)', key_part, re.IGNORECASE)
    if match:
        parts = [p.strip().title() for p in match.group(1).split(',') if p.strip()]
        return '/'.join(parts) if parts else None

    parts = key_part.split(';')
    if len(parts) > 1:
        ignore = {'INTERNET', 'QUOTED-PRINTABLE', 'BASE64', 'ENCODING', 'CHARSET'}
        params = [
            p.strip().title()
            for p in parts[1:]
            if p.strip() and p.strip().upper() not in ignore
        ]
        return '/'.join(params) if params else None

    return None


def detect_encoding(key_part):
    """
    Return 'QUOTED-PRINTABLE', 'BASE64', or None.
    Handles v3.0+ ENCODING=... and v2.1 inline field;QUOTED-PRINTABLE:.
    """
    match = re.search(r'ENCODING=([A-Za-z0-9-]+)', key_part, re.IGNORECASE)
    if match:
        return match.group(1).upper()
    for part in key_part.upper().split(';')[1:]:
        if part.strip() in ('QUOTED-PRINTABLE', 'BASE64'):
            return part.strip()
    return None


def decode_qp(value):
    """Decode Quoted-Printable, trying UTF-8 then Latin-1."""
    try:
        return quopri.decodestring(value.encode()).decode('utf-8')
    except Exception:
        try:
            return quopri.decodestring(value.encode()).decode('latin-1')
        except Exception:
            return value


def unfold(content):
    """
    Normalize line endings and unfold wrapped vCard lines.
    Per spec, a line starting with a space or tab continues the previous line.
    """
    content = content.replace('\r\n', '\n').replace('\r', '\n')
    result = []
    for line in content.split('\n'):
        if line and line[0] in (' ', '\t'):
            if result:
                result[-1] += line[1:]
        else:
            result.append(line)
    return '\n'.join(result)


def strip_group(prop):
    """Strip vCard group prefix: 'item1.TEL' → 'TEL'."""
    return prop.split('.', 1)[1] if '.' in prop else prop


def unescape(value):
    """Unescape vCard text escape sequences."""
    return (
        value
        .replace('\\n', '\n')
        .replace('\\N', '\n')
        .replace('\\,', ',')
        .replace('\\;', ';')
    )


def format_date(value):
    """
    Format a vCard date value to human-readable.
      YYYYMMDD / YYYY-MM-DD  →  April 12, 1985
      --MMDD / --MM-DD       →  July 4  (no year)
      YYYY                   →  1985
      Unrecognized           →  returned as-is
    """
    if not value:
        return value

    date_part = value.split('T')[0]

    if date_part.startswith('--'):
        digits = date_part[2:].replace('-', '')
        if len(digits) == 4 and digits.isdigit():
            m, d = int(digits[:2]), int(digits[2:])
            if 1 <= m <= 12 and 1 <= d <= 31:
                return f"{MONTHS[m - 1]} {d}"
        return value

    # Handle slash-form dates (M/D/Y or D/M/Y)
    if '/' in date_part:
        parts = date_part.split('/')
        if len(parts) == 3:
            try:
                a, b, c = int(parts[0]), int(parts[1]), int(parts[2])
                # Detect format: if first > 12, must be D/M/Y (day/month/year)
                if a > 12:
                    d, m, y = a, b, c
                # If second > 12, must be M/D/Y with b as day
                elif b > 12:
                    m, d, y = a, b, c
                # Ambiguous: assume US format M/D/Y
                else:
                    m, d, y = a, b, c
                # Handle 2-digit years: 00-30 → 2000-2030, 31-99 → 1931-1999
                if y < 100:
                    y = 2000 + y if y <= 30 else 1900 + y
                if 1 <= m <= 12 and 1 <= d <= 31:
                    return f"{MONTHS[m - 1]} {d}, {y}"
            except (ValueError, IndexError):
                pass
        return value

    # Handle numeric dates (YYYYMMDD, YYYYMM, YYYY)
    digits = date_part.replace('-', '')
    if digits.isdigit():
        if len(digits) == 8:
            y, m, d = int(digits[:4]), int(digits[4:6]), int(digits[6:])
            if 1 <= m <= 12 and 1 <= d <= 31:
                return f"{MONTHS[m - 1]} {d}, {y}"
        elif len(digits) == 6:
            # YYYYMM format (month/year only)
            y, m = int(digits[:4]), int(digits[4:6])
            if 1 <= m <= 12:
                return f"{MONTHS[m - 1]} {y}"
        elif len(digits) == 4:
            return digits

    return value


def format_datetime(value):
    """
    Format a vCard datetime value to human-readable with time.
      YYYYMMDDTHHMMSSz  →  April 12, 1985, 12:00 UTC
      Date only         →  delegates to format_date
    """
    if not value:
        return value
    if 'T' not in value:
        return format_date(value)

    date_part, time_part = value.split('T', 1)
    formatted = format_date(date_part)
    time_digits = re.sub(r'[^0-9]', '', time_part)
    if len(time_digits) >= 4:
        hh, mm = time_digits[:2], time_digits[2:4]
        tz = ' UTC' if time_part.upper().endswith('Z') else ''
        return f"{formatted}, {hh}:{mm}{tz}"
    return formatted


def safe_output_path(path):
    """
    Return a Path that does not yet exist.
    If path exists, appends _1, _2, ... until a free name is found.
    """
    p = Path(path)
    if not p.exists():
        return p
    counter = 1
    while True:
        candidate = p.parent / f"{p.stem}_{counter}{p.suffix}"
        if not candidate.exists():
            return candidate
        counter += 1


def has_displayable_content(contact):
    """
    Return True if the contact has at least one field worth showing.
    A contact with only _skipped, _version, _source, or empty custom fields
    is treated as having no displayable content and counted as malformed.
    """
    for field in DISPLAYABLE_FIELDS:
        if bool(contact.get(field)):
            return True
    # custom fields: check at least one has a non-empty value
    if any(v for v in contact.get('_custom', {}).values()):
        return True
    return False


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------

def parse_vcard(content):
    """
    Parse a single vCard block. Returns a contact dict, or {} if unparseable.
    The vCard version string (e.g. '3.0') is stored internally as '_version'.
    """
    content = unfold(content)
    contact = {}
    skipped = []
    custom = {}
    version = None

    for line in content.strip().split('\n'):
        line = line.strip()
        if not line or ':' not in line:
            continue

        key_part, value = line.split(':', 1)
        key_part = key_part.strip()
        value = value.strip()

        prop = strip_group(key_part.split(';')[0]).upper()

        # Capture version for reporting
        if prop == 'VERSION':
            version = value
            continue

        encoding = detect_encoding(key_part)

        if encoding == 'BASE64':
            if prop not in SILENT_FIELDS:
                skipped.append(f"{prop}: Base64 encoded data (skipped)")
            continue

        if encoding == 'QUOTED-PRINTABLE':
            value = decode_qp(value)

        if prop in SILENT_FIELDS:
            continue

        try:
            if prop == 'FN':
                contact['name'] = value

            elif prop == 'N':
                if not contact.get('name'):
                    parts = value.split(';')
                    # vCard N field order: family;given;additional;prefix;suffix
                    # We reassemble as: prefix given additional family suffix
                    name_parts = [
                        parts[i] for i in (3, 1, 2, 0, 4)
                        if i < len(parts) and parts[i]
                    ]
                    contact['name'] = ' '.join(name_parts).strip()

            elif prop == 'TEL':
                if not value:
                    raise ValueError("Empty phone number")
                value = strip_uri_prefix(value)
                if sum(c.isdigit() for c in value) < 5:
                    raise ValueError(f"Too short: {value}")
                label = extract_type(key_part)
                entry = f"Phone: {value} ({label})" if label else f"Phone: {value}"
                contact.setdefault('phones', []).append(entry)

            elif prop == 'EMAIL':
                if not value:
                    raise ValueError("Empty email")
                value = strip_uri_prefix(value)
                if value.count('@') != 1:
                    raise ValueError(f"Invalid email: {value}")
                local, domain = value.split('@')
                if not local or not domain or '.' not in domain:
                    raise ValueError(f"Invalid email: {value}")
                label = extract_type(key_part)
                entry = f"Email: {value} ({label})" if label else f"Email: {value}"
                contact.setdefault('emails', []).append(entry)

            elif prop in ('ADR', 'ADDR'):
                parts = [unescape(p) for p in value.split(';')]
                addr_parts = [parts[i] for i in range(2, 7) if i < len(parts) and parts[i]]
                address = ', '.join(addr_parts)
                if address:
                    label = extract_type(key_part)
                    entry = f"{address} ({label})" if label else address
                    contact.setdefault('addresses', []).append(entry)

            elif prop == 'ORG':
                if value:
                    contact.setdefault('organizations', []).append(value)

            elif prop == 'TITLE':
                if value:
                    contact['title'] = value

            elif prop == 'URL':
                if value:
                    contact.setdefault('urls', []).append(value)

            elif prop == 'NOTE':
                if value:
                    contact.setdefault('notes', []).append(unescape(value))

            elif prop == 'BDAY':
                if not value:
                    raise ValueError("Empty birthday")
                clean = value.replace('-', '').split('T')[0]
                valid = (
                    # YYYYMMDD or YYYY-MM-DD — full date
                    (clean.isdigit() and len(clean) == 8) or
                    # YYYYMM or YYYY-MM — month/year only
                    (clean.isdigit() and len(clean) == 6) or
                    # YYYY — year only
                    (clean.isdigit() and len(clean) == 4) or
                    # --MMDD or --MM-DD — vCard 4.0 no-year format
                    (value.startswith('--') and value[2:].replace('-', '').isdigit()) or
                    # Slash-form: M/D/Y or D/M/Y
                    ('/' in value and len(value.split('/')) == 3) or
                    # Month-name forms (e.g. "April 12, 1985")
                    any(m in value.lower() for m in [
                        'jan', 'feb', 'mar', 'apr', 'may', 'jun',
                        'jul', 'aug', 'sep', 'oct', 'nov', 'dec',
                    ])
                )
                if not valid:
                    raise ValueError(f"Unrecognized format: {value}")
                contact['birthday'] = format_date(value)

            elif prop == 'NICKNAME':
                if value:
                    contact['nickname'] = value

            elif prop == 'LABEL':
                if value:
                    contact['label'] = unescape(value)

            elif prop == 'ANNIVERSARY':
                if value:
                    contact['anniversary'] = format_date(value)

            elif prop == 'GENDER':
                if value:
                    contact['gender'] = value

            elif prop == 'CATEGORIES':
                if value:
                    cats = [c.strip() for c in value.split(',') if c.strip()]
                    if cats:
                        contact['categories'] = ', '.join(cats)

            elif prop == 'CREATED':
                if value:
                    contact['created'] = format_datetime(value)
                    contact['_created_raw'] = value  # preserve raw for merge_contacts

            elif prop in ('REVISED', 'REV'):
                if value:
                    contact['revised'] = format_datetime(value)
                    contact['_revised_raw'] = value  # preserve raw for is_newer and merge_contacts

            else:
                if prop and prop not in STANDARD_FIELDS:
                    clean_prop = prop[2:] if prop.startswith('X-') else prop
                    if clean_prop == 'LABEL':
                        if value:
                            contact['label'] = unescape(value)
                    else:
                        if value:
                            custom[clean_prop.replace('-', ' ').title()] = value

        except (ValueError, IndexError, AttributeError) as e:
            skipped.append(f"{prop}: {e}")

    # Remove duplicate values within each list field
    for key in ('phones', 'emails', 'addresses', 'urls', 'notes', 'organizations'):
        if key in contact:
            seen = []
            for item in contact[key]:
                if item not in seen:
                    seen.append(item)
            contact[key] = seen

    if skipped:
        contact['_skipped'] = skipped
    if custom:
        contact['_custom'] = custom
    if version:
        contact['_version'] = version

    return contact


# ---------------------------------------------------------------------------
# Formatter
# ---------------------------------------------------------------------------

def format_contact(contact):
    """Render a contact dict as a human-readable text block."""
    lines = []

    lines.append(f"Name: {contact['name']}" if contact.get('name') else "Name: (Unknown)")

    for org in contact.get('organizations', []):
        lines.append(f"Organization: {org}")

    if contact.get('title'):
        lines.append(f"Title: {contact['title']}")

    for phone in contact.get('phones', []):
        lines.append(phone)

    for email in contact.get('emails', []):
        lines.append(email)

    for addr in contact.get('addresses', []):
        lines.append(f"Address: {addr}")

    for url in contact.get('urls', []):
        lines.append(f"Website: {url}")

    if contact.get('birthday'):
        lines.append(f"Birthday: {contact['birthday']}")

    for note in contact.get('notes', []):
        lines.append(f"Note: {note}")

    if contact.get('nickname'):
        lines.append(f"Nickname: {contact['nickname']}")

    if contact.get('label'):
        lines.append(f"Label: {contact['label']}")

    if contact.get('anniversary'):
        lines.append(f"Anniversary: {contact['anniversary']}")

    if contact.get('gender'):
        lines.append(f"Gender: {contact['gender']}")

    if contact.get('categories'):
        lines.append(f"Categories: {contact['categories']}")

    if contact.get('created'):
        lines.append(f"Created: {contact['created']}")

    if contact.get('revised'):
        lines.append(f"Revised: {contact['revised']}")

    for field_name, field_value in contact.get('_custom', {}).items():
        lines.append(f"* {field_name}: {field_value}")

    if contact.get('_skipped'):
        lines.append("")
        lines.append("[Skipped Fields]")
        for msg in contact['_skipped']:
            lines.append(f"  ⚠ {msg}")

    return '\n'.join(lines)


# ---------------------------------------------------------------------------
# Duplicate detection
# ---------------------------------------------------------------------------

def identity_key(contact):
    """
    Build a hashable identity key from fields that define who a person is.
    Metadata fields (revised, created, notes, categories, custom) are excluded.

    Tuple positions:
      0 — name
      1 — phones (bare values, no type labels)
      2 — emails (bare values, no type labels)
      3 — addresses
      4 — organizations
      5 — birthday

    If new identity fields are added to the script (e.g. IMPP),
    add them here too or duplicate detection will miss differences in that field.
    """
    def bare(entries):
        result = set()
        for e in entries:
            val = e.split(':', 1)[1].split('(')[0].strip() if ':' in e else e
            result.add(val.lower())
        return frozenset(result)

    return (
        (contact.get('name') or '').strip().lower(),
        bare(contact.get('phones', [])),
        bare(contact.get('emails', [])),
        bare(contact.get('addresses', [])),
        frozenset(o.lower() for o in contact.get('organizations', [])),
        (contact.get('birthday') or '').lower(),
    )


def merge_contacts(base, duplicate):
    """
    Merge a duplicate contact into the base contact.
    Identity fields (phones, emails, addresses, orgs) are already the same
    by definition — no need to merge those.

    Meaningful non-identity fields are merged if missing from base:
      title, nickname, anniversary, gender, categories, urls, label

    Notes and custom fields from duplicate are appended (not overwritten)
    with a warning logged so the user knows data came from a removed duplicate.

    Revised:  keep the newer timestamp  (most recent edit wins)
    Created:  keep the earlier timestamp (oldest origin wins)
    """
    # Fields: take from duplicate only if base is missing
    for field in ('title', 'nickname', 'anniversary', 'gender', 'categories', 'label'):
        if not base.get(field) and duplicate.get(field):
            base[field] = duplicate[field]

    # URLs: merge unique values
    if duplicate.get('urls'):
        existing = set(base.get('urls', []))
        for url in duplicate['urls']:
            if url not in existing:
                base.setdefault('urls', []).append(url)
                existing.add(url)

    # Notes from duplicate appended with marker, skip if same content already exists
    if duplicate.get('notes'):
        base.setdefault('notes', [])
        existing_bare = {n.replace('[merged] ', '') for n in base['notes']}
        for note in duplicate['notes']:
            if note not in existing_bare:
                marked = f"[merged] {note}"
                if marked not in base['notes']:
                    base['notes'].append(marked)

    # Custom fields: merge unique keys, don't overwrite existing
    if duplicate.get('_custom'):
        base.setdefault('_custom', {})
        for key, val in duplicate['_custom'].items():
            if key not in base['_custom']:
                base['_custom'][key] = val

    # Revised: keep the newer timestamp (compare raw ISO strings, not formatted display strings)
    if duplicate.get('_revised_raw') and base.get('_revised_raw'):
        if duplicate['_revised_raw'] > base['_revised_raw']:
            base['revised'] = duplicate['revised']
            base['_revised_raw'] = duplicate['_revised_raw']
    elif duplicate.get('_revised_raw') and not base.get('_revised_raw'):
        base['revised'] = duplicate['revised']
        base['_revised_raw'] = duplicate['_revised_raw']

    # Created: keep the earlier timestamp — oldest origin date is the true one
    if duplicate.get('_created_raw') and base.get('_created_raw'):
        if duplicate['_created_raw'] < base['_created_raw']:
            base['created'] = duplicate['created']
            base['_created_raw'] = duplicate['_created_raw']
    elif duplicate.get('_created_raw') and not base.get('_created_raw'):
        base['created'] = duplicate['created']
        base['_created_raw'] = duplicate['_created_raw']

    return base


def is_newer(a, b):
    """
    Return True if contact a has a newer revised timestamp than b.
    Uses the raw vCard datetime string (_revised_raw) for comparison,
    not the formatted display string — ISO 8601 compares correctly as strings.
    If either is missing, returns False (keep existing base).
    """
    rev_a = a.get('_revised_raw') or ''
    rev_b = b.get('_revised_raw') or ''
    if not rev_a or not rev_b:
        return False
    return rev_a > rev_b


def classify_duplicates(contacts):
    """
    Two-tier duplicate classification:

    Exact  — all identity fields match → merge meaningful extra fields,
             newer REV contact becomes base, duplicate removed and reported.
    Fuzzy  — same name + at least one shared phone or email → kept, warned only.

    Returns (kept, exact_removed, fuzzy_warnings):
      kept          : list of contacts after exact merge/removal
      exact_removed : list of (retained_contact_number, name)
      fuzzy_warnings: list of (i, j, name), 1-based indices into kept
    """
    # key → index in kept list (for merging)
    seen = {}
    kept = []
    exact_removed = []

    for contact in contacts:
        key = identity_key(contact)
        if key in seen:
            kept_idx = seen[key]
            existing = kept[kept_idx]
            # REV-aware: newer contact becomes base, older is merged into it
            if is_newer(contact, existing):
                kept[kept_idx] = merge_contacts(contact, existing)
            else:
                kept[kept_idx] = merge_contacts(existing, contact)
            # Store (retained_contact_number, name) for warning output.
            # Fuzzy pass only warns, never removes, so this index stays accurate.
            exact_removed.append((kept_idx + 1, contact.get('name') or '(Unknown)'))
        else:
            seen[key] = len(kept)
            kept.append(contact)

    def phone_vals(c):
        return {
            p.split(':', 1)[1].split('(')[0].strip().lower()
            for p in c.get('phones', [])
        }

    def email_vals(c):
        return {
            e.split(':', 1)[1].split('(')[0].strip().lower()
            for e in c.get('emails', [])
        }

    fuzzy_warnings = []
    for i in range(len(kept)):
        for j in range(i + 1, len(kept)):
            a, b = kept[i], kept[j]
            name_a = (a.get('name') or '').strip().lower()
            name_b = (b.get('name') or '').strip().lower()
            if not name_a or not name_b or name_a != name_b:
                continue
            if phone_vals(a) & phone_vals(b) or email_vals(a) & email_vals(b):
                fuzzy_warnings.append((i + 1, j + 1, a.get('name', '(Unknown)')))

    return kept, exact_removed, fuzzy_warnings


# ---------------------------------------------------------------------------
# Converter
# ---------------------------------------------------------------------------

def convert(input_files, output_file, single_mode=False, sort_contacts=False, stats_only=False):
    """
    Parse one or more .vcf files and write all contacts to a text file.
    Auto-renames the output file if it already exists.
    """
    all_contacts = []
    malformed = 0
    total_found = 0

    for path_str in input_files:
        path = Path(path_str)
        if not path.exists():
            print(f"  ! File not found: {path_str}")
            continue

        print(f"  Reading {path.name} ...", end=' ', flush=True)

        try:
            content = path.read_text(encoding='utf-8')
        except UnicodeDecodeError:
            content = path.read_text(encoding='latin-1')

        blocks = re.split(r'END:VCARD\s*', content, flags=re.IGNORECASE)
        blocks = [b + 'END:VCARD' for b in blocks if re.search(r'BEGIN:VCARD', b, re.IGNORECASE)]

        file_contacts = []
        file_malformed = 0
        for block in blocks:
            contact = parse_vcard(block)
            if contact and has_displayable_content(contact):
                contact['_source'] = path.name
                file_contacts.append(contact)
            else:
                file_malformed += 1

        total_found += len(file_contacts) + file_malformed
        malformed += file_malformed

        n_contacts = len(file_contacts)
        n_malformed = file_malformed
        status = f"{n_contacts} {'contact' if n_contacts == 1 else 'contacts'}"
        if n_malformed:
            status += f", {n_malformed} malformed"
        print(status)

        all_contacts.extend(file_contacts)

    if not all_contacts:
        print("\n  No contacts found.")
        if malformed:
            m = malformed
            print(f"  {m} malformed {'block' if m == 1 else 'blocks'} skipped.")
        return False

    # Skip sort in stats-only mode — order is never shown so sorting is wasted work
    if sort_contacts and not stats_only:
        all_contacts.sort(key=lambda c: (
            not bool(c.get('name')),
            (c.get('name') or '').lower(),
        ))

    all_contacts, exact_removed, fuzzy_warnings = classify_duplicates(all_contacts)

    # Collect stats (used by both --stats mode and full output)
    total_skipped_fields = sum(len(c.get('_skipped', [])) for c in all_contacts)
    contacts_with_skips  = sum(1 for c in all_contacts if c.get('_skipped'))
    versions_found       = sorted({c.get('_version') for c in all_contacts if c.get('_version')})

    contacts_parts = [f"{total_found} found"]
    if malformed:
        contacts_parts.append(f"{malformed} malformed")
    if exact_removed:
        n_removed = len(exact_removed)
        contacts_parts.append(f"{n_removed} {'duplicate' if n_removed == 1 else 'duplicates'} removed")
    contacts_parts.append(f"{len(all_contacts)} exported")
    contacts_line = ', '.join(contacts_parts)

    # Stats-only mode: print summary and exit without writing a file
    if stats_only:
        print(f"\n  {DIVIDER}")
        print(f"  Contacts    :  {contacts_line}")
        if versions_found:
            print(f"  vCard       :  {', '.join(versions_found)}")
        if total_skipped_fields:
            fields_str   = f"{total_skipped_fields} {'field' if total_skipped_fields == 1 else 'fields'}"
            contacts_str = f"{contacts_with_skips} {'contact' if contacts_with_skips == 1 else 'contacts'}"
            print(f"  Skipped     :  {fields_str} across {contacts_str}")
        if fuzzy_warnings:
            w = len(fuzzy_warnings)
            print(f"  Warnings    :  {w} duplicate {'warning' if w == 1 else 'warnings'}")
        print(f"  {DIVIDER}")
        return True

    out_path = safe_output_path(output_file)
    if out_path != Path(output_file):
        print(f"\n  '{Path(output_file).name}' already exists — saving as '{out_path.name}'")

    # Build source line
    if single_mode:
        source_label = 'Source'
        source_value = Path(input_files[0]).name
    else:
        source_label = 'Sources'
        names = [Path(f).name for f in input_files]
        if len(names) <= 3:
            source_value = ', '.join(names)
        else:
            source_value = f"{', '.join(names[:2])}, and {len(names) - 2} more"

    # Assemble header
    now = datetime.now().strftime('%B %d, %Y, %H:%M')
    header_rows = [
        ('Exported',  now),
        (source_label, source_value),
    ]
    if not single_mode:
        n = len(input_files)
        header_rows.append(('Files', f"{n} {'file' if n == 1 else 'files'}"))
    header_rows.append(('Contacts', contacts_line))
    if versions_found:
        header_rows.append(('vCard versions', ', '.join(versions_found)))
    if total_skipped_fields:
        sf = total_skipped_fields
        cs = contacts_with_skips
        skip_str = f"{sf} {'field' if sf == 1 else 'fields'} across {cs} {'contact' if cs == 1 else 'contacts'}"
        header_rows.append(('Skipped fields', skip_str))
    if fuzzy_warnings:
        header_rows.append(('Duplicate warnings', f"{len(fuzzy_warnings)} (review in warnings section)"))
    if sort_contacts:
        header_rows.append(('Sorted', 'A to Z'))

    col_width = max(len(r[0]) for r in header_rows)
    header_lines = [f"  {label:<{col_width}}  :  {value}" for label, value in header_rows]

    lines = []
    lines.append("Generated by vCard2text")
    lines.append(DIVIDER)
    lines.extend(header_lines)
    lines.append(DIVIDER)
    lines.append("")

    for i, contact in enumerate(all_contacts, 1):
        if single_mode:
            header = f"⭐ Contact {i}:"
        else:
            header = f"⭐ Contact {i}: (from {contact.get('_source', '?')})"
        lines.append(header)
        lines.append(DIVIDER_CTX)
        lines.append(format_contact(contact))
        lines.append("")

    # Conversion warnings at the bottom
    warn_lines = []
    if malformed:
        b = 'block' if malformed == 1 else 'blocks'
        warn_lines.append(f"  ⚠ {malformed} malformed vCard {b} skipped (no parseable content)")
    if exact_removed:
        n_ex = len(exact_removed)
        d = 'duplicate' if n_ex == 1 else 'duplicates'
        warn_lines.append(f"  ⚠ {n_ex} exact {d} removed (newer revision kept where available):")
        for retained_idx, name in exact_removed:
            warn_lines.append(f"      - {name} → merged into Contact {retained_idx}")
    if fuzzy_warnings:
        for i, j, name in fuzzy_warnings:
            warn_lines.append(f"  ⚠ Duplicate warning: Contact {i} and Contact {j} ({name})")

    if warn_lines:
        lines.append(DIVIDER_HVY)
        lines.append("[Conversion Warnings]")
        lines.extend(warn_lines)
        lines.append(DIVIDER_HVY)

    try:
        out_path.write_text('\n'.join(lines), encoding='utf-8')
    except OSError as e:
        print(f"\n  ! Could not write output file: {e}")
        return False

    # Terminal summary
    print(f"\n  {DIVIDER}")
    print(f"  Contacts    :  {contacts_line}")
    if versions_found:
        print(f"  vCard       :  {', '.join(versions_found)}")
    if total_skipped_fields:
        fields_str   = f"{total_skipped_fields} {'field' if total_skipped_fields == 1 else 'fields'}"
        contacts_str = f"{contacts_with_skips} {'contact' if contacts_with_skips == 1 else 'contacts'}"
        print(f"  Skipped     :  {fields_str} across {contacts_str}")
    if fuzzy_warnings:
        w = len(fuzzy_warnings)
        print(f"  Warnings    :  {w} duplicate {'warning' if w == 1 else 'warnings'} — review output file")
    if sort_contacts:
        print(f"  Sorted      :  A to Z")
    print(f"  Output      :  {out_path}")
    print(f"  {DIVIDER}")

    return True


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    if '--version' in sys.argv:
        print(f"vCard2text {__version__}")
        sys.exit(0)

    if len(sys.argv) < 2 or '--help' in sys.argv or '-h' in sys.argv:
        print("vCard2text — Convert vCard files to readable text")
        print("=" * 50)
        print("Usage:")
        print("  python vCard2text.py <file.vcf> [options]")
        print("  python vCard2text.py *.vcf -o contacts.txt")
        print()
        print("Options:")
        print("  -o <file>    Output file (default: same name as input, .txt)")
        print("  --sort       Sort contacts A to Z")
        print("  --stats      Show summary statistics only, no output file written")
        print("  --version    Show program version")
        print("  -h, --help   Show this help")
        print()
        print("Examples:")
        print("  python vCard2text.py contacts.vcf")
        print("  python vCard2text.py contacts.vcf --sort -o out.txt")
        print("  python vCard2text.py contacts.vcf --stats")
        print("  python vCard2text.py file1.vcf file2.vcf -o merged.txt")
        sys.exit(0 if '--help' in sys.argv or '-h' in sys.argv else 1)

    args = sys.argv[1:]
    output_file   = None
    sort_contacts = '--sort' in args
    stats_only    = '--stats' in args

    args = [a for a in args if a not in ('--sort', '--stats')]

    if '-o' in args:
        idx = args.index('-o')
        if idx + 1 < len(args):
            output_file = args[idx + 1]
            args = args[:idx] + args[idx + 2:]
        else:
            print("Error: -o flag requires a filename.")
            sys.exit(1)

    if not args:
        print("Error: No input files specified.")
        sys.exit(1)

    input_files = []
    for pattern in args:
        matches = glob.glob(pattern)
        if matches:
            input_files.extend(matches)
        elif Path(pattern).exists():
            input_files.append(pattern)
        else:
            print(f"  ! No files matched: {pattern}")

    input_files = [f for f in input_files if f.lower().endswith('.vcf')]

    if not input_files:
        print("Error: No .vcf files found.")
        sys.exit(1)

    single_mode = len(input_files) == 1

    if output_file is None:
        if single_mode:
            output_file = str(Path(input_files[0]).with_suffix('.txt'))
        else:
            names = [Path(f).stem for f in input_files]
            output_file = (
                f"{names[0]}_{names[1]}.txt" if len(names) == 2
                else f"{names[0]}_and_{len(names) - 1}_more.txt"
            )

    n = len(input_files)
    print(f"\nvCard2text — {n} {'file' if n == 1 else 'files'} to process\n")
    convert(input_files, output_file, single_mode=single_mode, sort_contacts=sort_contacts, stats_only=stats_only)


if __name__ == "__main__":
    main()