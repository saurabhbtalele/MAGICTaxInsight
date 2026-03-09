"""Script to debug what Docling outputs for a given PDF."""
import json
import sys
from pathlib import Path

from docling.document_converter import DocumentConverter

def main():
    if len(sys.argv) < 2:
        print("Usage: python src/debug_docling.py <path_to_pdf>")
        sys.exit(1)

    pdf_path = Path(sys.argv[1])
    if not pdf_path.exists():
        print(f"File not found: {pdf_path}")
        sys.exit(1)

    print(f"Loading Docling DocumentConverter...")
    converter = DocumentConverter()
    
    print(f"Converting {pdf_path}...")
    result = converter.convert(str(pdf_path))
    
    markdown_text = result.document.export_to_markdown()
    json_text = json.dumps(result.document.export_to_dict(), indent=2)
    
    md_out = Path("output") / f"{pdf_path.stem}_docling.md"
    json_out = Path("output") / f"{pdf_path.stem}_docling.json"
    
    md_out.parent.mkdir(exist_ok=True)
    
    md_out.write_text(markdown_text, encoding="utf-8")
    json_out.write_text(json_text, encoding="utf-8")
    
    print(f"\n--- Markdown Preview ---")
    print(markdown_text[:1000] + "\n...\n")
    
    print(f"Saved MD output to: {md_out}")
    print(f"Saved JSON output to: {json_out}")

if __name__ == "__main__":
    main()
