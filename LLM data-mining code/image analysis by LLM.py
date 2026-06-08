from pathlib import Path
from openai import OpenAI
import base64
import mimetypes
import time
import os
import csv

root_dir = Path.cwd() / "LLM data-mining result"

# ====== Batch processing log file ======
batch_log_file = root_dir / "batch_image_analysis.csv"

# ====== llama.cpp server settings ======
base_url = os.environ.get("LLAMA_BASE_URL", "http://127.0.0.1:18080/v1")
model_id = os.environ.get("LLAMA_MODEL", "local-model")

client = OpenAI(
    base_url=base_url,
    api_key="no-key"
)


def image_to_data_url(image_path: Path) -> str:
    """Convert an image file to a base64 data URL for OpenAI-compatible APIs."""
    mime_type, _ = mimetypes.guess_type(str(image_path))
    if mime_type is None:
        mime_type = "image/png"

    data = image_path.read_bytes()
    b64 = base64.b64encode(data).decode("utf-8")

    return f"data:{mime_type};base64,{b64}"


def analyze_one_paper(paper_dir: Path) -> dict:
    """Analyze page images in the pages folder of a single paper directory."""

    pages_dir = paper_dir / "pages"
    out_file = paper_dir / "image_analysis.md"

    # ====== Processing record for a single paper ======
    result = {
        "paper_dir": str(paper_dir),
        "paper_name": paper_dir.name,
        "status": "failed",
        "image_count": 0,
        "prepare_time_s": None,
        "llm_time_s": None,
        "total_time_s": None,
        "avg_llm_time_per_image_s": None,
        "output_file": str(out_file),
        "error": "",
    }

    # ====== Check whether the pages folder exists ======
    if not pages_dir.exists():
        result["status"] = "skipped_no_pages"
        result["error"] = f"Pages folder not found: {pages_dir}"
        print(result["error"])
        return result

    # ====== Collect image files from the pages folder ======
    image_paths = []
    for ext in ["*.png", "*.jpg", "*.jpeg", "*.webp"]:
        image_paths.extend(pages_dir.glob(ext))

    image_paths = sorted(image_paths)

    # ====== Skip this paper if no image files are found ======
    if not image_paths:
        result["status"] = "skipped_no_images"
        result["error"] = f"No image files found in: {pages_dir}"
        print(result["error"])
        return result

    result["image_count"] = len(image_paths)

    print("\n" + "=" * 80)
    print(f"Analyzing paper: {paper_dir.name}")
    print(f"Pages directory: {pages_dir}")
    print(f"Number of images: {len(image_paths)}")
    print(f"Output file: {out_file}")

    total_start = time.perf_counter()

    try:
        # ====== Prepare image input content ======
        prepare_start = time.perf_counter()

        image_contents = []

        for i, image_path in enumerate(image_paths, start=1):
            image_contents.append({
                "type": "text",
                "text": f"Image {i}: {image_path.name}"
            })
            image_contents.append({
                "type": "image_url",
                "image_url": {
                    "url": image_to_data_url(image_path)
                }
            })

        prepare_end = time.perf_counter()
        prepare_time = prepare_end - prepare_start

        # ====== Build the image order manifest ======
        page_manifest = "\n".join(
            [f"Image {i}: {p.name}" for i, p in enumerate(image_paths, start=1)]
        )

        # ====== Build the multimodal prompt ======
        prompt = f"""
You are an expert in Chemical Looping.

Please analyze the provided images, which are pages from a literature paper discussing oxygen carriers, and answer the following questions.

Image order:
{page_manifest}

Questions:
1. Extract the DOI.
2. Do these images contain one of the following figures: (1) XRD pattern, (2) TGA/O2 evolution curve?
3. If the images contain figures about XRD, TGA, TG, DTG, TPD, or O2 evolution, identify in which figure or panel they are displayed, e.g., Figure 1, Figure 2, Figure 3a, Figure S18.
4. If XRD is present, identify the compound/material being measured. If there are multiple compounds, separate them by commas.
5. If TGA, TG, DTG, TPD, or O2 evolution is present, identify the compound/material being measured. If there are multiple compounds, separate them by commas.

Important definition:
- O2 evolution refers only to oxygen-related signals or curves, including O2 evolution, oxygen evolution, O2 release, oxygen release, oxygen production, and O2 release amount. 
- Do not count CO evolution, CO release, CO production, CO concentration curve, CO signal, CO2 evolution, CO2 release, or CO2 concentration curve as O2 evolution.
- Do not count H2-TPR, CO-TPR, CH4-TPR, or temperature-programmed reduction as TGA/TG/DTG/TPD/O2 evolution evidence.

Output requirements:
- Analyze all images together.
- Give only one final summary table for the whole paper.
- Do not output one result for each image.
- If a figure is mentioned in text but not visually shown, clearly state "mentioned but not shown".
- If exact information is uncertain, write "uncertain" instead of guessing.

Output format:

| DOI | XRD figure present | XRD in which figure | TGA/TG/DTG/TPD/O2 evolution figure present | TGA/TG/DTG/TPD/O2 evolution in which figure |
|---|---|---|---|---|
| ... | ... | ... | ... | ... |

Then give:

XRD compound/material identification:
...

TGA/TG/DTG/TPD/O2 evolution compound/material identification:
...

Evidence:
Briefly explain which pages or figures support the conclusion.
"""

        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    *image_contents
                ]
            }
        ]

        # ====== Call the LLM and measure processing time ======
        llm_start = time.perf_counter()

        response = client.chat.completions.create(
            model=model_id,
            messages=messages,
            temperature=0.0,
            max_tokens=10000,
        )

        llm_end = time.perf_counter()
        llm_time = llm_end - llm_start

        answer = response.choices[0].message.content or ""

        # ====== Compatibility for some thinking models: use reasoning_content if content is empty ======
        if not answer and hasattr(response.choices[0].message, "reasoning_content"):
            answer = response.choices[0].message.reasoning_content or ""

        # ====== Save the model output ======
        out_file.write_text(answer, encoding="utf-8")

        total_end = time.perf_counter()
        total_time = total_end - total_start

        # ====== Record success status and timing information ======
        result["status"] = "success"
        result["prepare_time_s"] = round(prepare_time, 2)
        result["llm_time_s"] = round(llm_time, 2)
        result["total_time_s"] = round(total_time, 2)
        result["avg_llm_time_per_image_s"] = round(llm_time / len(image_paths), 2)

        print("Analysis completed.")
        print(f"Result saved to: {out_file}")

        print("\n====== Timing statistics ======")
        print(f"Number of images: {len(image_paths)}")
        print(f"Image preparation/base64 encoding time: {prepare_time:.2f} s")
        print(f"LLM image processing and response generation time: {llm_time:.2f} s")
        print(f"Total script runtime: {total_time:.2f} s")
        print(f"Average LLM time per image: {llm_time / len(image_paths):.2f} s/image")

        print("\n====== Model output ======")
        print(answer)

    except Exception as e:
        # ====== Record failure status and error message ======
        total_end = time.perf_counter()
        total_time = total_end - total_start

        result["status"] = "failed"
        result["total_time_s"] = round(total_time, 2)
        result["error"] = str(e)

        error_file = paper_dir / "image_analysis_error_llamacpp.txt"
        error_file.write_text(str(e), encoding="utf-8")

        print(f"Analysis failed for paper: {paper_dir.name}")
        print(f"Error message: {e}")
        print(f"Error saved to: {error_file}")

    return result


def main():
    print(f"root_dir: {root_dir}")
    print(f"base_url: {base_url}")
    print(f"model_id: {model_id}")

    # ====== Check whether the root directory exists ======
    if not root_dir.exists():
        raise FileNotFoundError(f"Root directory does not exist: {root_dir}")

    # ====== Get all paper subdirectories under the root directory ======
    paper_dirs = sorted([p for p in root_dir.iterdir() if p.is_dir()])

    print(f"Found {len(paper_dirs)} paper subdirectories.")

    batch_results = []

    batch_start = time.perf_counter()

    # ====== Analyze papers one by one ======
    for idx, paper_dir in enumerate(paper_dirs, start=1):
        print("\n" + "#" * 80)
        print(f"Progress: {idx}/{len(paper_dirs)}")
        print(f"Current paper: {paper_dir.name}")

        result = analyze_one_paper(paper_dir)
        batch_results.append(result)

        # ====== Write the log after each paper to avoid data loss if the script stops midway ======
        with batch_log_file.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=[
                    "paper_dir",
                    "paper_name",
                    "status",
                    "image_count",
                    "prepare_time_s",
                    "llm_time_s",
                    "total_time_s",
                    "avg_llm_time_per_image_s",
                    "output_file",
                    "error",
                ]
            )
            writer.writeheader()
            writer.writerows(batch_results)

    batch_end = time.perf_counter()
    batch_time = batch_end - batch_start

    # ====== Print batch processing statistics ======
    print("\n" + "=" * 80)
    print("All papers have been processed.")
    print(f"Total number of papers: {len(paper_dirs)}")
    print(f"Log file: {batch_log_file}")
    print(f"Total batch runtime: {batch_time:.2f} s")

    success_count = sum(1 for r in batch_results if r["status"] == "success")
    failed_count = sum(1 for r in batch_results if r["status"] == "failed")
    skipped_count = len(batch_results) - success_count - failed_count

    print(f"Successful: {success_count}")
    print(f"Failed: {failed_count}")
    print(f"Skipped: {skipped_count}")


if __name__ == "__main__":
    main()