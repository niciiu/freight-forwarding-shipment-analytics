"""Clean raw shipment records for downstream PostgreSQL loading.

This script reads the raw shipment Excel file, applies approved data quality
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
    "etd",
    "eta",
    "actual_departure",
    "actual_arrival",
    "cut_off_time",
    "closing_time",
    "created_date",
    "last_update_timestamp",
]

NUMERIC_COLUMNS = [
    "cargo_volume_cbm",
    "total_charge_usd",
    "container_qty",
]


def load_data() -> pd.DataFrame:
    """Load the raw shipments Excel file."""
    return pd.read_excel(RAW_DATA_DIR / "shipments.xlsx")


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


def standardize_shipping_lines(df: pd.DataFrame) -> pd.DataFrame:
    """Standardize approved shipping line name variants."""
    cleaned_df = df.copy()
    shipping_line_mapping = {
        "bluewave lines": "BlueWave Lines",
        "BLUEWAVE LINES": "BlueWave Lines",
        "Blue Wave Lines": "BlueWave Lines",
        "BlueWave Lines": "BlueWave Lines",
        "BlueWaev Lines": "BlueWave Lines",
        "OceanLink Shipping": "OceanLink Shipping",
        "oceanlink shipping": "OceanLink Shipping",
        "OCEANLINK SHIPPING": "OceanLink Shipping",
        "Pacific Horizon Shipping": "Pacific Horizon Shipping",
        "pacific horizon shipping": "Pacific Horizon Shipping",
        "PACIFIC HORIZON SHIPPING": "Pacific Horizon Shipping",
    }

    cleaned_df["shipping_line"] = cleaned_df["shipping_line"].map(
        lambda value: shipping_line_mapping.get(value, value)
    )
    return cleaned_df


def standardize_origin_ports(df: pd.DataFrame) -> pd.DataFrame:
    """Standardize approved origin port name variants."""
    cleaned_df = df.copy()
    origin_port_mapping = {
        "SHANGHAI": "Shanghai",
        "Shanghai": "Shanghai",
        "Port Klangg": "Port Klang",
        "Singpore": "Singapore",
        "Hong Kong": "Hong Kong",
    }

    cleaned_df["origin_port"] = cleaned_df["origin_port"].map(
        lambda value: origin_port_mapping.get(value, value)
    )
    return cleaned_df


def standardize_customer_names(df: pd.DataFrame) -> pd.DataFrame:
    """Standardize approved customer name variants."""
    cleaned_df = df.copy()
    customer_name_mapping = {
        "Custmer Holdings": "Customer Holdings",
    }

    cleaned_df["customer_name"] = cleaned_df["customer_name"].map(
        lambda value: customer_name_mapping.get(value, value)
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


def save_processed_data(df: pd.DataFrame) -> None:
    """Save the cleaned shipments dataframe as a processed CSV file."""
    PROCESSED_DATA_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(PROCESSED_DATA_DIR / "shipments_clean.csv", index=False)


def print_validation_report(
    df: pd.DataFrame,
    rows_before: int,
    duplicate_rows_removed: int,
    invalid_numeric_count: int,
    invalid_datetime_count: int,
) -> None:
    """Print the final cleaning validation report."""
    print(f"Rows before cleaning: {rows_before}")
    print(f"Rows after cleaning: {df.shape[0]}")
    print(f"Duplicate rows removed: {duplicate_rows_removed}")
    print(
        "Number of invalid numeric values converted to NaN: "
        f"{invalid_numeric_count}"
    )
    print(
        "Number of invalid datetime values converted to NaT: "
        f"{invalid_datetime_count}"
    )
    print(f"Final dataframe shape: {df.shape}")
    print("Final dataframe dtypes:")
    print(df.dtypes)


def main() -> None:
    """Run the shipment cleaning workflow."""
    shipments_df = load_data()
    rows_before = shipments_df.shape[0]

    shipments_df = standardize_column_names(shipments_df)
    shipments_df = clean_string_columns(shipments_df)
    shipments_df = standardize_shipping_lines(shipments_df)
    shipments_df = standardize_origin_ports(shipments_df)
    shipments_df = standardize_customer_names(shipments_df)
    shipments_df, invalid_datetime_count = parse_datetime_columns(shipments_df)
    shipments_df, invalid_numeric_count = parse_numeric_columns(shipments_df)
    shipments_df, duplicate_rows_removed = remove_duplicates(shipments_df)

    save_processed_data(shipments_df)
    print_validation_report(
        df=shipments_df,
        rows_before=rows_before,
        duplicate_rows_removed=duplicate_rows_removed,
        invalid_numeric_count=invalid_numeric_count,
        invalid_datetime_count=invalid_datetime_count,
    )


if __name__ == "__main__":
    main()
