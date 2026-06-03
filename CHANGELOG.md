# Changelog

## [2.0] — Current

Complete rewrite and overhaul from v1.0 (original GitHub release).

### Fixed

- Lowercase property names not parsed — `.upper()` normalization added
- Group prefix not stripped — `item1.TEL` now correctly parsed as `TEL`
- Windows `\r\n` line endings not normalized before processing
- Quoted-Printable decoding missing for vCard 2.1 inline style (`NOTE;QUOTED-PRINTABLE:`)
- `--MMDD` birthday format (vCard 4.0 year-omitted) incorrectly rejected
- Multiple `ORG` values silently overwritten — now collected as a list
- Multiple `URL` values silently overwritten — now collected as a list
- Multiple `NOTE` values silently overwritten — now collected as a list
- `REV` field treated as unknown custom field — now shown as `Revised:`
- `key_part` not stripped before parsing
- `ADR` escape sequences (`\,`, `\n`, `\;`) not unescaped in address values
- `CATEGORIES` output raw — now cleaned and comma-space padded
- Phone and email lines were indented inconsistently — all fields now flush left
- Type label casing inconsistent — now always Title Case (`Work/Voice/Pref`)
- `item1.X-LABEL` incorrectly landed in custom fields — now routes to `Label:`
- `is_base64()` dead code removed
- `STANDARD_FIELDS` constant defined but never used — now wired into custom field logic
- Two near-identical converter functions merged into one
- Birthday and anniversary stored as raw vCard strings — now formatted (e.g. `April 12, 1985`)
- `--stats` mode ran a full sort step unnecessarily — skipped in stats-only mode now
- Exact duplicate removal discarded unique data from the removed contact — now merged
- `TITLE`, `NICKNAME`, `LABEL`, `GENDER` empty values stored — now guarded with `if value:`
- `NOTE` empty value stored empty string in notes list — now guarded
- `CATEGORIES` with only whitespace or commas stored empty string — now guarded
- `CREATED` and `REVISED`/`REV` empty values stored — now guarded
- Custom `X-` fields with empty values stored — now guarded
- `is_newer()` compared formatted display strings instead of raw ISO timestamps — now uses `_revised_raw`
- `merge_contacts()` note dedup missed same content without `[merged]` prefix — fixed
- All-empty-field contacts incorrectly counted as valid — caught by `has_displayable_content()`
- `-o` with no filename silently fell back to default output name — now errors clearly
- `merge_contacts()` revised comparison used formatted strings — now uses `_revised_raw`
- `Files` row shown twice in terminal output (once at top, once in summary table) — removed from table
- `file(s)`, `contact(s)`, `field(s)` bracket notation in terminal — proper singular/plural throughout
- `merge_contacts()` docstring said it merged `created` but implementation did not — now implemented
- Duplicate `--version` check in `main()` — dead code removed
- Single mode contact header missing trailing colon — now consistent (`⭐ Contact 1:`)
- `_created_raw` comment incorrectly referenced `is_newer()` — corrected to `merge_contacts`
- `exact_removed` comment said index was "approximate" — indices are exact (fuzzy pass never removes)
- 6-digit date format (`YYYYMM`) validator and formatter now consistent — formats as `April 1985`
- Slash-form date validator used loose `'/' in value` check — now requires exactly 3 parts

### Added

- Two-tier duplicate contact detection:
  - Exact duplicates (all identity fields match) — merged and removed, reported in warnings
  - Fuzzy duplicates (same name + shared phone or email) — kept, warned only
- Smart merge on exact duplicates — unique data rescued from removed contact:
  - `title`, `nickname`, `anniversary`, `gender`, `categories`, `label`, `urls` — taken from duplicate if missing in base
  - `notes` — appended with `[merged]` prefix; skipped if same content already exists
  - Custom `X-` fields — merged, base wins on conflict
  - `revised` — newer `_revised_raw` wins
  - `created` — earlier `_created_raw` wins (oldest origin date is the true one)
- REV-aware base selection — contact with newer `REV` timestamp becomes primary; older merged into it
- Warning output now shows which contact a duplicate merged into: `- John Smith → merged into Contact 3`
- Field-level deduplication — identical values within the same contact removed
- `--sort` flag — sort contacts A to Z, unknowns last
- `--stats` flag — print summary statistics only, no output file written
- `--version` flag — print `vCard2text 2.0` and exit
- `-o` with no filename now errors cleanly: `Error: -o flag requires a filename.`
- Auto-rename output if file already exists (`contacts_1.txt`, `contacts_2.txt`, ...)
- Smart output filename when no `-o` given (single / two / three-or-more files)
- Human-readable output file header with all relevant rows; missing rows suppressed
- `Files:` row in output file header for multi-file runs
- `⭐ Contact N:` decoration on each contact header
- Contact count line: `10 found, 1 malformed, 1 duplicate removed, 8 exported`
- `[Conversion Warnings]` section at bottom of output file
- Per-contact `[Skipped Fields]` section with `⚠` warnings for invalid fields
- `format_date` — human-readable dates for birthday/anniversary
- `format_datetime` — human-readable datetimes with time component
- Slash-form date support (`4/12/1985` → `April 12, 1985`; 2-digit years handled)
- 6-digit date support (`YYYYMM` → `April 1985`)
- `has_displayable_content()` — all-empty-field vCards counted as malformed
- `DISPLAYABLE_FIELDS` constant
- `_revised_raw` and `_created_raw` stored alongside formatted values for correct ISO comparison
- `safe_output_path()` — auto-rename logic
- `unescape()` — centralised vCard escape sequence handling
- `is_newer()` — REV-aware timestamp comparison using raw ISO strings
- `merge_contacts()` — field merge logic with correct revised/created handling
- Error handling on output file write — clean message on permission denied / disk full
- File encoding detection: UTF-8 with Latin-1 fallback
- vCard version detection per contact, aggregated in header
- `identity_key` tuple positions documented in code comments
- Proper singular/plural throughout all terminal output

### Changed

- `X-` vendor field prefix stripped from display name (`X-SKYPE` → `* Skype:`)
- Custom fields shown with `*` prefix
- `detect_encoding` handles both v2.1 and v3.0+ encoding styles
- `extract_type` returns consistent Title Case output
- `unfold` also normalizes `\r\n` before unfolding
- Section dividers unified via `DIVIDER`, `DIVIDER_HVY`, `DIVIDER_CTX` constants

---

## [1.0] — Original GitHub Release

Initial release. Basic vCard to text conversion.
Single file input, UTF-8/Latin-1 encoding support, wildcard file patterns.
Supports vCard 2.1, 3.0, 4.0 (partial).
