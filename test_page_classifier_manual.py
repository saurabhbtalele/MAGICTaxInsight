from pathlib import Path

from src.utils import classify_pdf_pages, PageType


def main() -> None:
    pdf_path = Path("samples/page_classifier_test.pdf")
    print(f"Exists: {pdf_path.exists()} at {pdf_path.resolve()}")

    if not pdf_path.exists():
        raise FileNotFoundError(pdf_path)

    result = classify_pdf_pages(pdf_path)

    print("\nTotal pages:", result.total_pages)
    print("all_selectable:", result.all_selectable)
    print("all_image:", result.all_image)
    print("has_mixed_pages:", result.has_mixed_pages)
    print("is_scanned_document:", result.is_scanned_document)

    print("\nPer-page:")
    for p in result.pages:
        print(
            f"  page {p.page_number}: type={p.page_type.value}, "
            f"chars={p.char_count}, image_area_ratio={p.image_area_ratio:.2f}, "
            f"confidence={p.confidence:.2f}"
        )


if __name__ == "__main__":
    main()

