from src.parsers.base_parser import _PARSER_REGISTRY, get_form_parser
from src.forms.registry import _SCHEMA_REGISTRY, get_form_schema
import src.forms # Trigger registration

print("--- REGISTRY SANITY CHECK ---")
print(f"Schemas registered: {len(_SCHEMA_REGISTRY)}")
for (fid, yr) in sorted(_SCHEMA_REGISTRY.keys(), key=lambda x: (x[0], x[1] if x[1] is not None else 0)):
    print(f"  [SCHEMA] {fid} / {yr}")

print(f"\nParsers registered: {len(_PARSER_REGISTRY)}")
for (fid, yr) in sorted(_PARSER_REGISTRY.keys(), key=lambda x: (x[0], x[1] if x[1] is not None else 0)):
    print(f"  [PARSER] {fid} / {yr}")

# Test fallback logic
print("\n--- FALLBACK LOGIC TEST ---")
parser_2025 = get_form_parser("1120-S", 2025)
print(f"get_form_parser('1120-S', 2025) -> {parser_2025.__name__ if parser_2025 else 'None'}")

parser_2023 = get_form_parser("1120-S", 2023)
print(f"get_form_parser('1120-S', 2023) -> {parser_2023.__name__ if parser_2023 else 'None'}")

if parser_2025 and parser_2025.__name__ == 'Form1120SParser2023':
    print("\nSUCCESS: 2025 correctly fell back to 2023 parser!")
else:
    print("\nFAILURE: Fallback logic incorrect.")
