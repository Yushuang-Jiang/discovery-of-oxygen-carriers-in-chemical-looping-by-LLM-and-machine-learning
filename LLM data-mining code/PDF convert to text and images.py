from pathlib import Path
import argparse
import fitz  # PyMuPDF
from tqdm import tqdm


def convert_one_pdf(pdf_path: Path, source_root: Path, output_root: Path, dpi: int = 220):
    """
    Convert a single PDF into:
    1. full_text.txt
    2. pages/page_001.png, page_002.png, ...
    """

    relative_path = pdf_path.relative_to(source_root)
    pdf_output_dir = output_root / relative_path.parent / pdf_path.stem
    pages_dir = pdf_output_dir / "pages"

    pdf_output_dir.mkdir(parents=True, exist_ok=True)
    pages_dir.mkdir(parents=True, exist_ok=True)

    txt_path = pdf_output_dir / "full_text.txt"

    try:
        doc = fitz.open(pdf_path)
    except Exception as e:
        return False, f"Failed to open PDF: {pdf_path}. Error: {e}"

    zoom = dpi / 72
    matrix = fitz.Matrix(zoom, zoom)

    all_text = []

    try:
        for page_index, page in enumerate(doc, start=1):
            # 1. Extract text from the current page
            text = page.get_text("text") or ""
            all_text.append(
                f"\n\n===== Page {page_index} =====\n\n{text}"
            )

            # 2. Render the full page as an image
            image_path = pages_dir / f"page_{page_index:03d}.png"
            pix = page.get_pixmap(matrix=matrix, alpha=False)
            pix.save(image_path)

        txt_path.write_text("".join(all_text), encoding="utf-8")

    except Exception as e:
        return False, f"Conversion failed: {pdf_path}. Error: {e}"

    finally:
        doc.close()

    return True, f"Completed: {pdf_path}"


def main():
    parser = argparse.ArgumentParser(
        description="Batch convert all PDF files in a folder into text files and page images."
    )

    parser.add_argument(
        "--source",
        default=r"C:\Users\JYS\Desktop\PDF_files",
        help="Root directory containing PDF files."
    )

    parser.add_argument(
        "--output",
        default=None,
        help="Output directory. If not specified, the output folder will be created next to the source folder."
    )

    parser.add_argument(
        "--dpi",
        type=int,
        default=400,
        help="Image resolution for PDF page rendering. Default: 400. Common choices: 150, 200, 300, 400."
    )

    # Use this line in Jupyter Notebook
    args = parser.parse_args(args=[])

    source_root = Path(args.source)

    if not source_root.exists():
        raise FileNotFoundError(f"Source directory does not exist: {source_root}")

    if args.output is None:
        output_root = source_root.parent / f"{source_root.name}_converted_results"
    else:
        output_root = Path(args.output)

    output_root.mkdir(parents=True, exist_ok=True)

    pdf_files = sorted(source_root.rglob("*.pdf"))

    if not pdf_files:
        print(f"No PDF files found in: {source_root}")
        return

    print(f"Found {len(pdf_files)} PDF files.")
    print(f"Source directory: {source_root}")
    print(f"Output directory: {output_root}")
    print(f"Image DPI: {args.dpi}")
    print("-" * 60)

    failed = []

    for pdf_path in tqdm(pdf_files, desc="Converting PDFs"):
        success, message = convert_one_pdf(
            pdf_path=pdf_path,
            source_root=source_root,
            output_root=output_root,
            dpi=args.dpi
        )

        if not success:
            failed.append(message)

    print("\nAll files have been processed.")
    print(f"Output directory: {output_root}")

    if failed:
        log_path = output_root / "failed_files.txt"
        log_path.write_text("\n".join(failed), encoding="utf-8")
        print(f"{len(failed)} files failed to process. See details in: {log_path}")
    else:
        print("All PDF files were processed successfully.")


if __name__ == "__main__":
    main()