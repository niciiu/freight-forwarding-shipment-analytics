"""Clean raw issue log records for PostgreSQL loading.

This script reads the raw issue log Excel file, applies approved data quality
cleaning rules, and writes a processed CSV. It does not calculate business
metrics, perform SQL, or modify the raw source file.
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
    "issue_open_date",
    "due_date",
    "issue_closed_date",
    "last_update_timestamp",
]

OUTPUT_FILE = PROCESSED_DATA_DIR / "issue_log_clean.csv"


def load_data() -> pd.DataFrame:
    """Load the raw issue log Excel file."""
    return pd.read_excel(RAW_DATA_DIR / "issue_log.xlsx")


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


def remove_duplicates(df: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    """Remove only fully duplicated rows."""
    rows_before = df.shape[0]
    cleaned_df = df.drop_duplicates()
    duplicate_rows_removed = rows_before - cleaned_df.shape[0]
    return cleaned_df, duplicate_rows_removed


def save_processed_data(df: pd.DataFrame) -> Path:
    """Save the cleaned issue log dataframe as a processed CSV file."""
    PROCESSED_DATA_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUTPUT_FILE, index=False)
    return OUTPUT_FILE


def print_validation_report(
    df: pd.DataFrame,
    rows_before: int,
    duplicate_rows_removed: int,
    invalid_datetime_count: int,
    output_file_path: Path,
) -> None:
    """Print the final cleaning validation report."""
    print(f"Rows before cleaning: {rows_before}")
    print(f"Rows after cleaning: {df.shape[0]}")
    print(f"Duplicate rows removed: {duplicate_rows_removed}")
    print(
        "Invalid datetime values converted to NaT: "
        f"{invalid_datetime_count}"
    )
    print(f"Final dataframe shape: {df.shape}")
    print("Final dataframe dtypes:")
    print(df.dtypes)
    print(f"Output file path: {output_file_path}")


def main() -> None:
    """Run the issue log cleaning workflow."""
    issue_log_df = load_data()
    rows_before = issue_log_df.shape[0]

    issue_log_df = standardize_column_names(issue_log_df)
    issue_log_df = clean_string_columns(issue_log_df)
    issue_log_df, invalid_datetime_count = parse_datetime_columns(issue_log_df)
    issue_log_df, duplicate_rows_removed = remove_duplicates(issue_log_df)

    output_file_path = save_processed_data(issue_log_df)
    print_validation_report(
        df=issue_log_df,
        rows_before=rows_before,
        duplicate_rows_removed=duplicate_rows_removed,
        invalid_datetime_count=invalid_datetime_count,
        output_file_path=output_file_path,
    )


if __name__ == "__main__":
    main()
