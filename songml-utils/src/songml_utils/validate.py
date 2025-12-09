"""SongML validation CLI - parses and outputs AST as JSON."""

import sys
from .parser import parse_songml
from .ast import ParseError, Section, Property


def main():
    """CLI entry point for songml-validate command."""
    if len(sys.argv) < 2:
        print("Usage: songml-validate <file.songml>", file=sys.stderr)
        sys.exit(1)
    
    filename = sys.argv[1]
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            content = f.read()
        
        doc = parse_songml(content)
        
        # Validation messages to stderr
        print(f"✓ Parsed successfully: {len(doc.items)} top-level items", file=sys.stderr)
        
        if doc.warnings:
            print(f"\nWarnings ({len(doc.warnings)}):", file=sys.stderr)
            for warning in doc.warnings:
                print(f"  {warning}", file=sys.stderr)
        
        # Print summary to stderr
        section_count = sum(1 for item in doc.items if isinstance(item, Section))
        property_count = sum(1 for item in doc.items if isinstance(item, Property))
        print(f"\nSummary: {section_count} sections, {property_count} properties", file=sys.stderr)
        
        # AST JSON to stdout
        print(doc.to_json())
        
    except ParseError as e:
        print(f"✗ Parse error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"✗ Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
