#!/usr/bin/env python3
"""
vCard2text - vCard to Text File Converter
Converts vCard (.vcf) files into a readable text format
"""

import sys
import re
import glob
from pathlib import Path


def parse_vcard(vcard_content):
    """Parse a single vCard entry and extract key information."""
    contact = {}
    lines = vcard_content.strip().split('\n')
    
    for line in lines:
        line = line.strip()
        
        # Handle line continuations (lines starting with space/tab)
        if line.startswith(' ') or line.startswith('\t'):
            continue
            
        if ':' not in line:
            continue
            
        # Split on first colon
        key_part, value = line.split(':', 1)
        
        # Extract the property name (before any semicolon parameters)
        prop = key_part.split(';')[0]
        
        # Map common vCard properties
        if prop == 'FN':
            contact['name'] = value
        elif prop == 'N':
            # N property: Family;Given;Middle;Prefix;Suffix
            parts = value.split(';')
            if not contact.get('name'):  # Use FN if available, otherwise construct
                name_parts = [parts[3], parts[1], parts[2], parts[0], parts[4]]
                contact['name'] = ' '.join(p for p in name_parts if p).strip()
        elif prop == 'TEL':
            phones = contact.get('phones', [])
            # Extract type if present
            phone_type = 'Phone'
            if 'TYPE=' in key_part.upper():
                type_match = re.search(r'TYPE=([^;:]+)', key_part.upper())
                if type_match:
                    phone_type = type_match.group(1).replace(',', '/').title()
            phones.append(f"{phone_type}: {value}")
            contact['phones'] = phones
        elif prop == 'EMAIL':
            emails = contact.get('emails', [])
            email_type = 'Email'
            if 'TYPE=' in key_part.upper():
                type_match = re.search(r'TYPE=([^;:]+)', key_part.upper())
                if type_match:
                    email_type = type_match.group(1).replace(',', '/').title()
            emails.append(f"{email_type}: {value}")
            contact['emails'] = emails
        elif prop == 'ADR':
            # ADR: ;;Street;City;State;Postal;Country
            parts = value.split(';')
            addr_parts = [parts[2], parts[3], parts[4], parts[5], parts[6]]
            address = ', '.join(p for p in addr_parts if p)
            if address:
                contact['address'] = address
        elif prop == 'ORG':
            contact['organization'] = value
        elif prop == 'TITLE':
            contact['title'] = value
        elif prop == 'URL':
            contact['url'] = value
        elif prop == 'NOTE':
            contact['note'] = value
        elif prop == 'BDAY':
            contact['birthday'] = value
    
    return contact


def format_contact(contact):
    """Format a contact dictionary into readable text."""
    lines = []
    
    # Name (required)
    if contact.get('name'):
        lines.append(f"Name: {contact['name']}")
    else:
        lines.append("Name: (Unknown)")
    
    # Organization and title
    if contact.get('organization'):
        lines.append(f"Organization: {contact['organization']}")
    if contact.get('title'):
        lines.append(f"Title: {contact['title']}")
    
    # Phones
    if contact.get('phones'):
        for phone in contact['phones']:
            lines.append(f"  {phone}")
    
    # Emails
    if contact.get('emails'):
        for email in contact['emails']:
            lines.append(f"  {email}")
    
    # Address
    if contact.get('address'):
        lines.append(f"Address: {contact['address']}")
    
    # URL
    if contact.get('url'):
        lines.append(f"Website: {contact['url']}")
    
    # Birthday
    if contact.get('birthday'):
        lines.append(f"Birthday: {contact['birthday']}")
    
    # Note
    if contact.get('note'):
        lines.append(f"Note: {contact['note']}")
    
    return '\n'.join(lines)


def convert_vcf_to_text(input_file, output_file=None):
    """Convert a vCard file to text format."""
    input_path = Path(input_file)
    
    if not input_path.exists():
        print(f"Error: File '{input_file}' not found.")
        return False
    
    # Read the vCard file
    try:
        with open(input_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except UnicodeDecodeError:
        # Try with different encoding
        with open(input_path, 'r', encoding='latin-1') as f:
            content = f.read()
    
    # Split into individual vCards
    vcards = re.split(r'END:VCARD\s*', content)
    vcards = [v + 'END:VCARD' for v in vcards if 'BEGIN:VCARD' in v]
    
    # Parse all contacts
    contacts = []
    for vcard in vcards:
        contact = parse_vcard(vcard)
        if contact:
            contacts.append(contact)
    
    # Generate output
    output_lines = []
    output_lines.append(f"vCard Contacts Export")
    output_lines.append(f"Total Contacts: {len(contacts)}")
    output_lines.append("=" * 60)
    output_lines.append("")
    
    for i, contact in enumerate(contacts, 1):
        output_lines.append(f"Contact {i}:")
        output_lines.append("-" * 40)
        output_lines.append(format_contact(contact))
        output_lines.append("")
    
    # Determine output file name
    if output_file is None:
        output_file = input_path.with_suffix('.txt')
    
    # Write to file
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(output_lines))
    
    print(f"Successfully converted {len(contacts)} contact(s)")
    print(f"Output written to: {output_file}")
    return True


def convert_multiple_vcf(input_files, output_file):
    """Convert multiple vCard files into a single text file."""
    all_contacts = []
    
    for input_file in input_files:
        input_path = Path(input_file)
        
        if not input_path.exists():
            print(f"Warning: File '{input_file}' not found. Skipping...")
            continue
        
        print(f"Processing: {input_file}")
        
        # Read the vCard file
        try:
            with open(input_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except UnicodeDecodeError:
            with open(input_path, 'r', encoding='latin-1') as f:
                content = f.read()
        
        # Split into individual vCards
        vcards = re.split(r'END:VCARD\s*', content)
        vcards = [v + 'END:VCARD' for v in vcards if 'BEGIN:VCARD' in v]
        
        # Parse all contacts from this file
        for vcard in vcards:
            contact = parse_vcard(vcard)
            if contact:
                contact['source_file'] = input_path.name
                all_contacts.append(contact)
    
    if not all_contacts:
        print("Error: No contacts found in any of the files.")
        return False
    
    # Generate output
    output_lines = []
    output_lines.append(f"vCard Contacts Export")
    output_lines.append(f"Source Files: {len(input_files)}")
    output_lines.append(f"Total Contacts: {len(all_contacts)}")
    output_lines.append("=" * 60)
    output_lines.append("")
    
    for i, contact in enumerate(all_contacts, 1):
        output_lines.append(f"Contact {i}: (from {contact.get('source_file', 'unknown')})")
        output_lines.append("-" * 40)
        output_lines.append(format_contact(contact))
        output_lines.append("")
    
    # Write to file
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(output_lines))
    
    print(f"\nSuccessfully converted {len(all_contacts)} contact(s) from {len(input_files)} file(s)")
    print(f"Output written to: {output_file}")
    return True


def main():
    if len(sys.argv) < 2:
        print("vCard2text - vCard to Text Converter")
        print("=" * 50)
        print("Usage: python vcard2text.py <input1.vcf> [input2.vcf ...] [-o output.txt]")
        print("\nExamples:")
        print("  python vcard2text.py contacts.vcf")
        print("  python vcard2text.py file1.vcf file2.vcf file3.vcf")
        print("  python vcard2text.py '*.vcf' -o all_contacts.txt")
        print("  python vcard2text.py file1.vcf file2.vcf -o output.txt")
        sys.exit(1)
    
    # Parse arguments
    args = sys.argv[1:]
    output_file = None
    input_patterns = []
    
    # Check for -o flag
    if '-o' in args:
        o_index = args.index('-o')
        if o_index + 1 < len(args):
            output_file = args[o_index + 1]
            # Remove -o and output filename from args
            args = args[:o_index] + args[o_index + 2:]
    
    input_patterns = args
    
    if not input_patterns:
        print("Error: No input files specified.")
        sys.exit(1)
    
    # Expand wildcards and collect all matching files
    input_files = []
    for pattern in input_patterns:
        matches = glob.glob(pattern)
        if matches:
            input_files.extend(matches)
        else:
            # If no glob matches, check if it's a literal filename
            if Path(pattern).exists():
                input_files.append(pattern)
            else:
                print(f"Warning: No files found matching '{pattern}'")
    
    # Filter to only .vcf files
    input_files = [f for f in input_files if f.lower().endswith('.vcf')]
    
    if not input_files:
        print("Error: No .vcf files found.")
        sys.exit(1)
    
    print(f"Found {len(input_files)} vCard file(s) to process")
    
    # Set default output file if not specified
    if output_file is None:
        if len(input_files) == 1:
            output_file = Path(input_files[0]).with_suffix('.txt')
        else:
            output_file = 'all_contacts.txt'
    
    # Convert
    if len(input_files) == 1:
        convert_vcf_to_text(input_files[0], output_file)
    else:
        convert_multiple_vcf(input_files, output_file)


if __name__ == "__main__":
    main()
