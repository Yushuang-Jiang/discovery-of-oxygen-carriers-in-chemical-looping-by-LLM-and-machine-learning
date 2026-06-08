from pathlib import Path
from openai import OpenAI
import time
import os
import csv


# ====== Root directory: "LLM data-mining result" folder under the current working directory ======
root_dir = Path.cwd() / "LLM data-mining result"

# ====== Batch processing log file ======
batch_log_file = root_dir / "batch_text_analysis.csv"

# ====== llama.cpp server settings ======
# The following environment variables can be set in the sbatch script:
# export LLAMA_BASE_URL="http://127.0.0.1:${PORT}/v1"
# export LLAMA_MODEL="local-model"
base_url = os.environ.get("LLAMA_BASE_URL", "http://127.0.0.1:18080/v1")
model_id = os.environ.get("LLAMA_MODEL", "local-model")

client = OpenAI(
    base_url=base_url,
    api_key="no-key"
)


def analyze_one_paper_text(paper_dir: Path) -> dict:
    """Analyze the full_text.txt file in a single paper directory."""

    txt_file = paper_dir / "full_text.txt"
    out_file = paper_dir / "text_analysis.md"

    result = {
        "paper_dir": str(paper_dir),
        "paper_name": paper_dir.name,
        "status": "failed",
        "text_length": 0,
        "llm_time_s": None,
        "total_time_s": None,
        "output_file": str(out_file),
        "error": "",
    }

    if not txt_file.exists():
        result["status"] = "skipped_no_text"
        result["error"] = f"full_text.txt not found: {txt_file}"
        print(result["error"])
        return result

    print("\n" + "=" * 80)
    print(f"Analyzing paper: {paper_dir.name}")
    print(f"Input file: {txt_file}")
    print(f"Output file: {out_file}")

    total_start = time.perf_counter()

    try:
        # ====== Read the full text ======
        full_text = txt_file.read_text(encoding="utf-8", errors="ignore")
        result["text_length"] = len(full_text)

        print(f"Text length: {len(full_text)} characters")

        # ====== Text analysis prompt ======
        prompt = f"""
You are an expert in Chemical Looping.

The following text is extracted from a literature paper discussing oxygen carriers.
Please analyze the full text and answer the following questions:

1. Extract the DOI.
2. Determine whether the paper contains XRD patterns.
3. If XRD patterns are present, identify the figure number or panel, e.g., Figure 1, Figure 3a, Figure S18.
4. Determine whether the paper contains TGA, TG, DTG, TPD, or O2 evolution figures.
5. If TGA/TG/DTG/TPD/O2 evolution figures are present, identify the figure number or panel.
6. If XRD is present, identify the compound or material measured. If there are multiple compounds, separate them by commas.
7. If TGA/TG/DTG/TPD/O2 evolution is present, identify the compound or material measured. If there are multiple compounds, separate them by commas.

Important definition:
- O2 evolution refers only to oxygen-related signals or curves, including O2 evolution, oxygen evolution, O2 release, oxygen release, oxygen production, and O2 release amount. 
- Do not count CO evolution, CO release, CO production, CO concentration curve, CO signal, CO2 evolution, CO2 release, or CO2 concentration curve as O2 evolution.
- Do not count H2-TPR, CO-TPR, CH4-TPR, or temperature-programmed reduction as TGA/TG/DTG/TPD/O2 evolution evidence.

Output requirements:
- Give only one summary table for the whole paper.
- Do not output page-by-page results.
- If a figure is only mentioned in the text but not clearly described, state "mentioned but uncertain".
- If exact information is uncertain, write "uncertain" instead of guessing.
- Do not output reasoning process. Only output the final answer.

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
Briefly explain the text evidence supporting the conclusion.

Full text:
{full_text}
"""

        # ====== Call the LLM and measure text processing time ======
        llm_start = time.perf_counter()

        response = client.chat.completions.create(
            model=model_id,
            messages=[
                {"role": "user", "content": prompt}
            ],
            temperature=0.0,
            max_tokens=128000,
        )

        llm_end = time.perf_counter()
        llm_time = llm_end - llm_start

        # ====== Get the model output ======
        message = response.choices[0].message
        answer = message.content or ""

        # ====== Compatibility for some thinking models: use reasoning_content if content is empty ======
        if not answer and hasattr(message, "reasoning_content"):
            answer = message.reasoning_content or ""

        # ====== Save the model output ======
        out_file.write_text(answer, encoding="utf-8")

        total_end = time.perf_counter()
        total_time = total_end - total_start

        result["status"] = "success"
        result["llm_time_s"] = round(llm_time, 2)
        result["total_time_s"] = round(total_time, 2)

        print("Text analysis completed.")
        print(f"Result saved to: {out_file}")
        print("\n====== Timing statistics ======")
        print(f"LLM text processing time: {llm_time:.2f} s")
        print(f"Total processing time for this paper: {total_time:.2f} s")

        print("\n====== Model output ======")
        print(answer)

    except Exception as e:
        total_end = time.perf_counter()
        total_time = total_end - total_start

        result["status"] = "failed"
        result["total_time_s"] = round(total_time, 2)
        result["error"] = str(e)

        error_file = paper_dir / "text_analysis_error_llamacpp.txt"
        error_file.write_text(str(e), encoding="utf-8")

        print(f"Analysis failed for paper: {paper_dir.name}")
        print(f"Error message: {e}")
        print(f"Error saved to: {error_file}")

    return result


def main():
    print(f"root_dir: {root_dir}")
    print(f"base_url: {base_url}")
    print(f"model_id: {model_id}")

    if not root_dir.exists():
        raise FileNotFoundError(f"Root directory does not exist: {root_dir}")

    paper_dirs = sorted([p for p in root_dir.iterdir() if p.is_dir()])

    print(f"Found {len(paper_dirs)} paper subdirectories.")

    batch_results = []
    batch_start = time.perf_counter()

    for idx, paper_dir in enumerate(paper_dirs, start=1):
        print("\n" + "#" * 80)
        print(f"Progress: {idx}/{len(paper_dirs)}")
        print(f"Current paper: {paper_dir.name}")

        result = analyze_one_paper_text(paper_dir)
        batch_results.append(result)

        # ====== Write the log after each paper to avoid data loss if the script stops midway ======
        with batch_log_file.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=[
                    "paper_dir",
                    "paper_name",
                    "status",
                    "text_length",
                    "llm_time_s",
                    "total_time_s",
                    "output_file",
                    "error",
                ]
            )
            writer.writeheader()
            writer.writerows(batch_results)

    batch_end = time.perf_counter()
    batch_time = batch_end - batch_start

    print("\n" + "=" * 80)
    print("All paper texts have been processed.")
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
