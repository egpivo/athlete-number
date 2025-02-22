import os

import pandas as pd
from config import OUTPUT_CSV


def process_results(results, processed_files):
    """Convert OCR results into structured format."""
    rows = []
    detected_files = {
        result.filename.split("/")[-1].split("_tn_")[0] for result in results
    }

    for result in results:
        filename = result.filename.split("/")[-1].split("_tn_")[0]
        if result.extracted_number:
            for tag in result.extracted_number:
                rows.append([filename, tag])
        else:
            rows.append([filename, None])

    for filename in processed_files:
        clean_filename = filename.split("/")[-1].split("_tn_")[0]
        if clean_filename not in detected_files:
            rows.append([clean_filename, None])

    return rows


def save_results_to_csv(results, processed_files):
    """Append detection results to a CSV file."""
    structured_results = process_results(results, processed_files)
    df = pd.DataFrame(structured_results, columns=["photonum", "tag"])

    df.to_csv(OUTPUT_CSV, mode="a", index=False, header=not os.path.exists(OUTPUT_CSV))

    print(f"Results saved to {OUTPUT_CSV}")
