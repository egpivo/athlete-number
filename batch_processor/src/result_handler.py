import os

import pandas as pd
from src.config import OUTPUT_CSV


def process_results(results):
    """Convert OCR results into structured format."""
    rows = []
    for result in results:
        eid, cid, photonum = result.filename.split("/")[-1].split("_")[:3]
        if result.extracted_number:
            for tag in result.extracted_number:
                rows.append([eid, cid, photonum, tag])
        else:
            rows.append([eid, cid, photonum, ""])

    return rows


def save_results_to_csv(results):
    """Append detection results to a CSV file."""
    structured_results = process_results(results)
    df = pd.DataFrame(structured_results, columns=["eid", "cid", "photonum", "tag"])

    df.to_csv(OUTPUT_CSV, mode="a", index=False, header=not os.path.exists(OUTPUT_CSV))

    print(f"Results saved to {OUTPUT_CSV}")
