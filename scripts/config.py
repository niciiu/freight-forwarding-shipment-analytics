"""Project configuration and environment loading.

This module centralizes reusable filesystem paths for the analytics project
and loads environment variables from a root-level .env file.

Database credentials and connection objects are intentionally not defined
here. Future scripts should read required settings from environment variables
without hardcoding secrets in source code.
"""

from pathlib import Path

from dotenv import load_dotenv


# Project root directory
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Common project directories
DATA_DIR = PROJECT_ROOT / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
NOTEBOOKS_DIR = PROJECT_ROOT / "notebooks"
SQL_DIR = PROJECT_ROOT / "sql"
DOCS_DIR = PROJECT_ROOT / "docs"

# Load environment variables from .env
load_dotenv(PROJECT_ROOT / ".env")