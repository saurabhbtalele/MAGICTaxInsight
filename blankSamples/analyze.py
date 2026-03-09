import asyncio
import json
from pathlib import Path
from src.batch_processor import process_batch

async def main():
    samples_dir = Path("blankSamples")
    pdf_paths = sorted(samples_dir.glob("*.pdf"))
    
    print(f"Analyzing {len(pdf_paths)} official blank forms...\n")
    
    results = await process_batch(pdf_paths)
    
    analysis_report = {}
    
    for r in results:
        doc_name = r.path.name
        analysis_report[doc_name] = {
            "success": r.success,
            "error": r.error,
            "detected_forms": [],
            "extracted_fields_count": 0
        }
        
        if r.success and r.data:
            forms = r.data.get("forms", [])
            for f in forms:
                form_id = f.get("form_id")
                fields = f.get("fields", {})
                num_fields = len([v for k, v in fields.items() if v is not None])
                
                analysis_report[doc_name]["detected_forms"].append({
                    "form_id": form_id,
                    "confidence": f.get("confidence", 0),
                    "extraction_tier": f.get("extraction_tier_used"),
                    "extracted_fields": num_fields
                })
                analysis_report[doc_name]["extracted_fields_count"] += num_fields

    with open("output/form_analysis_report.json", "w") as f:
        json.dump(analysis_report, f, indent=2)
        
    print("Report written to output/form_analysis_report.json")

if __name__ == "__main__":
    asyncio.run(main())
