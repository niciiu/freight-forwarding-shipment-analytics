"""Clean raw shipment milestone records for PostgreSQL loading.

This script reads the raw shipment milestones Excel file, applies approved
data quality cleaning rules, and writes a processed CSV. It does not calculate
business metrics, perform SQL, or modify the raw source file.
"""

import re
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from scripts.config import PROCESSED_DATA_DIR, RAW_DATA_DIR


DATETIME_COLUMNS = [
    "planned_datetime",
    "actual_datetime",
    "update_timestamp",
]

NUMERIC_COLUMNS = [
    "milestone_sequence",
]

OUTPUT_FILE = PROCESSED_DATA_DIR / "shipment_milestones_clean.csv"


def load_data() -> pd.DataFrame:
    """Load the raw shipment milestones Excel file."""
    return pd.read_excel(RAW_DATA_DIR / "shipment_milestones.xlsx")


def standardize_column_names(df: pd.DataFrame) -> pd.DataFrame:
    """Convert dataframe column names to snake_case."""
    cleaned_df = df.copy()
    cleaned_df.columns = [
        re.sub(r"_+", "_", re.sub(r"[^0-9a-zA-Z]+", "_", col.strip()))
        .strip("_")
        .lower()
        for col in cleaned_df.columns
    ]
    return cleaned_df


def clean_string_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Trim leading/trailing spaces and collapse repeated spaces in text columns."""
    cleaned_df = df.copy()
    string_columns = cleaned_df.select_dtypes(include=["object", "string"]).columns

    for column in string_columns:
        cleaned_df[column] = cleaned_df[column].map(
            lambda value: re.sub(r"\s+", " ", value.strip())
            if isinstance(value, str)
            else value
        )

    return cleaned_df


def standardize_milestone_status(df: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    """Standardize approved milestone status variants and count corrections."""
    cleaned_df = df.copy()
    status_mapping = {
        "completed": "Completed",
        "COMPLETED": "Completed",
        "delayed": "Delayed",
        "DELAYED": "Delayed",
        "pending": "Pending",
        "PENDING": "Pending",
    }

    original_values = cleaned_df["milestone_status"]
    corrected_values = original_values.map(
        lambda value: status_mapping.get(value, value)
    )
    correction_count = int(
        (
            original_values.notna()
            & corrected_values.notna()
            & (original_values != corrected_values)
        ).sum()
    )
    cleaned_df["milestone_status"] = corrected_values

    return cleaned_df, correction_count


def parse_datetime_columns(df: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    """Parse approved datetime columns and count invalid values converted to NaT."""
    cleaned_df = df.copy()
    invalid_datetime_count = 0

    for column in DATETIME_COLUMNS:
        original_values = cleaned_df[column]
        parsed_values = pd.to_datetime(original_values, errors="coerce")
        invalid_datetime_count += int(
            (original_values.notna() & parsed_values.isna()).sum()
        )
        cleaned_df[column] = parsed_values

    return cleaned_df, invalid_datetime_count


def parse_numeric_columns(df: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    """Parse approved numeric columns and count invalid values converted to NaN."""
    cleaned_df = df.copy()
    invalid_numeric_count = 0

    for column in NUMERIC_COLUMNS:
        original_values = cleaned_df[column]
        parsed_values = pd.to_numeric(original_values, errors="coerce")
        invalid_numeric_count += int(
            (original_values.notna() & parsed_values.isna()).sum()
        )
        cleaned_df[column] = parsed_values

    return cleaned_df, invalid_numeric_count


def remove_duplicates(df: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    """Remove only fully duplicated rows."""
    rows_before = df.shape[0]
    cleaned_df = df.drop_duplicates()
    duplicate_rows_removed = rows_before - cleaned_df.shape[0]
    return cleaned_df, duplicate_rows_removed


def save_processed_data(df: pd.DataFrame) -> Path:
    """Save the cleaned shipment milestones dataframe as a processed CSV file."""
    PROCESSED_DATA_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUTPUT_FILE, index=False)
    return OUTPUT_FILE


def print_validation_report(
    df: pd.DataFrame,
    rows_before: int,
    duplicate_rows_removed: int,
    status_correction_count: int,
    invalid_numeric_count: int,
    invalid_datetime_count: int,
    output_file_path: Path,
) -> None:
    """Print the final cleaning validation report."""
    print(f"Rows before cleaning: {rows_before}")
    print(f"Rows after cleaning: {df.shape[0]}")
    print(f"Duplicate rows removed: {duplicate_rows_removed}")
    print(f"Milestone Status corrections: {status_correction_count}")
    print(
        "Invalid numeric values converted to NaN: "
        f"{invalid_numeric_count}"
    )
    print(
        "Invalid datetime values converted to NaT: "
        f"{invalid_datetime_count}"
    )
    print(f"Final dataframe shape: {df.shape}")
    print("Final dataframe dtypes:")
    print(df.dtypes)
    print(f"Output file path: {output_file_path}")


def main() -> None:
    """Run the shipment milestones cleaning workflow."""
    milestones_df = load_data()
    rows_before = milestones_df.shape[0]

    milestones_df = standardize_column_names(milestones_df)
    milestones_df = clean_string_columns(milestones_df)
    milestones_df, status_correction_count = standardize_milestone_status(
        milestones_df
    )
    milestones_df, invalid_datetime_count = parse_datetime_columns(
        milestones_df
    )
    milestones_df, invalid_numeric_count = parse_numeric_columns(milestones_df)
    milestones_df, duplicate_rows_removed = remove_duplicates(milestones_df)

    output_file_path = save_processed_data(milestones_df)
    print_validation_report(
        df=milestones_df,
        rows_before=rows_before,
        duplicate_rows_removed=duplicate_rows_removed,
        status_correction_count=status_correction_count,
        invalid_numeric_count=invalid_numeric_count,
        invalid_datetime_count=invalid_datetime_count,
        output_file_path=output_file_path,
    )


if __name__ == "__main__":
    main()
