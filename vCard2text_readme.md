# vCard2text

A simple Python script that converts vCard (.vcf) files into readable text format. Perfect for backing up contacts, viewing contact information without a contacts app, or converting contacts for easy reading and searching.

## Features

- ✅ Parse single or multiple vCard files
- ✅ Support for vCard versions 2.1, 3.0, and 4.0
- ✅ Extract all common contact fields (name, phone, email, address, etc.)
- ✅ Handle multiple contacts per file
- ✅ Wildcard pattern support (*.vcf)
- ✅ Clean, readable text output
- ✅ UTF-8 and Latin-1 encoding support
- ✅ Track source file for each contact

## Requirements

- Python 3.6 or higher
- No external dependencies (uses only standard library)

## Installation

1. Download the `vcard2text.py` script
2. Make it executable (optional on Unix/Linux/Mac):
   ```bash
   chmod +x vcard2text.py
   ```

That's it! No pip install needed.

## Usage

### Basic Usage

Convert a single vCard file:
```bash
python vcard2text.py contacts.vcf
```
This creates `contacts.txt` in the same directory.

### Multiple Files

Convert multiple specific files:
```bash
python vcard2text.py file1.vcf file2.vcf file3.vcf
```
This creates `all_contacts.txt` with all contacts combined.

### Wildcard Patterns

Convert all .vcf files in the current directory:
```bash
python vcard2text.py "*.vcf"
```

Convert files matching a pattern:
```bash
python vcard2text.py "backup_*.vcf"
```

### Custom Output File

Specify your own output filename:
```bash
python vcard2text.py "*.vcf" -o my_contacts.txt
```

```bash
python vcard2text.py file1.vcf file2.vcf -o combined.txt
```

## Output Format

The script creates a well-formatted text file with:

```
vCard Contacts Export
Source Files: 2
Total Contacts: 15
============================================================

Contact 1: (from contacts1.vcf)
----------------------------------------
Name: John Smith
Organization: Acme Corp
Title: Software Engineer
  Mobile: +1-555-0123
  Work: +1-555-0199
  Work/Internet: john.smith@acme.com
Address: 123 Main St, San Francisco, CA, 94105, USA
Website: https://johnsmith.com

Contact 2: (from contacts2.vcf)
----------------------------------------
Name: Jane Doe
...
```

## Supported vCard Fields

The converter extracts the following information:

| Field | Description |
|-------|-------------|
| **Name** | Full name (FN) or constructed from name components (N) |
| **Organization** | Company or organization name |
| **Title** | Job title or position |
| **Phone Numbers** | All phone numbers with types (Mobile, Work, Home, etc.) |
| **Email Addresses** | All email addresses with types |
| **Address** | Physical address |
| **Website** | URL/website |
| **Birthday** | Date of birth |
| **Notes** | Additional notes or comments |

## Examples

### Example 1: Export iPhone Contacts

1. Export your iPhone contacts as vCard
2. Save the file (e.g., `iphone_contacts.vcf`)
3. Run:
   ```bash
   python vcard2text.py iphone_contacts.vcf
   ```

### Example 2: Merge Multiple Contact Backups

```bash
python vcard2text.py backup_2023.vcf backup_2024.vcf -o all_backups.txt
```

### Example 3: Convert All Contact Files in a Directory

```bash
python vcard2text.py "*.vcf" -o complete_contacts.txt
```

## Command Line Options

| Option | Description |
|--------|-------------|
| `<file.vcf>` | Input vCard file(s). Can specify multiple files or use wildcards |
| `-o <output.txt>` | Specify custom output filename (optional) |

**Default behavior:**
- Single file: Creates `filename.txt` (same name as input)
- Multiple files: Creates `all_contacts.txt`

## Tips

- **Quotes around wildcards**: Use quotes around patterns like `"*.vcf"` to ensure proper expansion
- **Multiple sources**: When processing multiple files, the output shows which file each contact came from
- **Encoding issues**: The script automatically tries UTF-8 first, then falls back to Latin-1 encoding
- **Empty fields**: Fields that are empty or not present in the vCard won't appear in the output
- **Large files**: The script efficiently handles large vCard files with hundreds of contacts

## Troubleshooting

**"No files found matching '*.vcf'"**
- Make sure you use quotes: `"*.vcf"`
- Check that .vcf files exist in the current directory
- Try specifying the full path: `"/path/to/files/*.vcf"`

**"Error: No .vcf files found"**
- Verify the files have the `.vcf` extension
- Check that you're in the correct directory
- Use `ls *.vcf` (Unix/Mac) or `dir *.vcf` (Windows) to verify files exist

**UnicodeDecodeError**
- The script handles this automatically by trying different encodings
- If you still see errors, the vCard file may be corrupted

**"No contacts found in any of the files"**
- Verify the file is a valid vCard format
- Open the .vcf file in a text editor and check for `BEGIN:VCARD` and `END:VCARD` tags
- Make sure the file isn't empty or corrupted

## File Format Details

vCard2text supports standard vCard format specifications:

**Recognized vCard Properties:**
- `FN` - Formatted name
- `N` - Name components (Family, Given, Middle, Prefix, Suffix)
- `TEL` - Telephone numbers (with TYPE parameter support)
- `EMAIL` - Email addresses (with TYPE parameter support)
- `ADR` - Postal addresses
- `ORG` - Organization/company name
- `TITLE` - Job title
- `URL` - Website URLs
- `BDAY` - Birthday
- `NOTE` - Notes and comments

**TYPE Parameter Support:**
Phone and email types are automatically detected and labeled (e.g., Work, Home, Mobile, Cell, Voice, Internet, etc.)

## License

This script is provided as-is for free use. Feel free to modify and distribute.

## Contributing

Found a bug or want to add a feature? Contributions are welcome!

## Common Use Cases

- 📱 Backup iPhone/Android contacts in readable format
- 📧 Convert email client contacts to text
- 🔍 Search through contacts with grep/find
- 📝 Create contact lists for documentation
- 💾 Archive old contact databases
- 🔄 Migrate between systems that don't share formats
- 📊 Generate reports from contact data
- 🔐 Keep offline backup of important contacts

## Platform Compatibility

- ✅ Windows
- ✅ macOS
- ✅ Linux
- ✅ Any system with Python 3.6+

---

**Program:** vCard2text  
**Version:** 1.0  
**Last Updated:** May 2026