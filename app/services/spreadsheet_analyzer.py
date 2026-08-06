"""
Load tenant Excel files from storage and run exact pandas calculations.
No hardcoded column names or domain-specific mapping — columns come from the file only.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Optional

import pandas as pd
from sqlalchemy.orm import Session

from app.services.document_service import get_document_for_tenant
from app.storage.minio_client import get_storage
from app.utils.logger import setup_logger

logger = setup_logger(__name__)

_EXCEL_SUFFIXES = {".xlsx", ".xls"}


def _normalize_column_name(name: str) -> str:
    """Compare columns ignoring case, spaces, and underscores."""
    return re.sub(r"[\s_]+", "", str(name).strip().lower())


def _normalize_cell_value(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value).strip().lower())


def _numeric_columns(df: pd.DataFrame) -> list[str]:
    numeric = df.select_dtypes(include="number").columns.tolist()
    if numeric:
        return [str(c) for c in numeric]
    found = []
    for col in df.columns:
        series = pd.to_numeric(df[col], errors="coerce")
        if series.notna().any():
            found.append(str(col))
    return found


def _resolve_column(df: pd.DataFrame, column: str) -> str:
    """Resolve column from the spreadsheet (case/space/underscore insensitive)."""
    if not column or not column.strip():
        raise ValueError("column is required for this operation")

    target = _normalize_column_name(column)
    for col in df.columns:
        if _normalize_column_name(col) == target:
            return str(col)

    available = ", ".join(str(c) for c in df.columns)
    raise ValueError(f"Column '{column}' not found. Available columns: {available}")


def _filter_rows_by_value(df: pd.DataFrame, column: str, match_value: str) -> tuple[str, pd.DataFrame]:
    col = _resolve_column(df, column)
    target = _normalize_cell_value(match_value)
    series = df[col].map(_normalize_cell_value)
    matches = df[series == target]
    if matches.empty:
        matches = df[series.str.contains(re.escape(target), case=False, na=False)]
    return col, matches


def _numeric_series(df: pd.DataFrame, column: str) -> tuple[pd.Series, str]:
    col = _resolve_column(df, column)
    series = pd.to_numeric(df[col], errors="coerce")
    if series.notna().sum() == 0:
        raise ValueError(f"Column '{col}' has no numeric values to calculate")
    return series, col


def _require_column(operation: str, column: Optional[str], df: pd.DataFrame) -> None:
    if column and str(column).strip():
        return
    available = ", ".join(str(c) for c in df.columns)
    raise ValueError(
        f"column is required for {operation}. "
        f"Call operation=columns first, then pass the exact column name. "
        f"Available: {available}"
    )


def load_excel_dataframe(db: Session, tenant_id: str, document_id: str) -> tuple[pd.DataFrame, str]:
    doc = get_document_for_tenant(db, tenant_id, document_id)
    filename = doc.filename or ""
    suffix = Path(filename).suffix.lower()
    if suffix not in _EXCEL_SUFFIXES:
        raise ValueError(f"Document '{filename}' is not an Excel file (.xlsx)")

    storage = get_storage()
    temp_path = None
    try:
        file_path = storage.download_to_temp(doc.file_path)
        if not Path(file_path).is_file():
            temp_path = file_path
        df = pd.read_excel(file_path, engine="openpyxl")
        if df.empty:
            raise ValueError("Spreadsheet is empty")
        return df, filename
    finally:
        if temp_path:
            storage.cleanup_temp(temp_path)


def _columns_containing_value(df: pd.DataFrame, key_value: str) -> list[str]:
    """Find which columns contain key_value (dynamic — no preset column names)."""
    target = str(key_value).strip().lower()
    if not target:
        return []

    found: list[str] = []
    for col in df.columns:
        series = df[col].astype(str).str.strip().str.lower()
        if (series == target).any():
            found.append(str(col))
            continue
        if series.str.contains(re.escape(target), case=False, na=False).any():
            found.append(str(col))
    return found


def lookup_spreadsheet_row(
    db: Session,
    tenant_id: str,
    document_id: str,
    key_value: str,
    key_column: Optional[str] = None,
    return_column: Optional[str] = None,
) -> dict[str, Any]:
    """
    Find row(s) by key_value. If key_column is omitted, searches all columns dynamically.
    """
    df, filename = load_excel_dataframe(db, tenant_id, document_id)

    if not key_value or not str(key_value).strip():
        raise ValueError("key_value is required for lookup")

    resolved_key_col = key_column
    if not resolved_key_col or not str(resolved_key_col).strip():
        candidates = _columns_containing_value(df, key_value)
        if len(candidates) == 1:
            resolved_key_col = candidates[0]
        elif len(candidates) > 1:
            raise ValueError(
                f"Value '{key_value}' appears in multiple columns: {', '.join(candidates)}. "
                "Pass key_column with the exact column name from operation=columns."
            )
        else:
            available = ", ".join(str(c) for c in df.columns)
            raise ValueError(
                f"No row found with value '{key_value}' in any column. "
                f"Available columns: {available}"
            )

    key_col = _resolve_column(df, resolved_key_col)
    target = str(key_value).strip().lower()
    series = df[key_col].astype(str).str.strip().str.lower()
    matches = df[series == target]
    if matches.empty:
        matches = df[series.str.contains(re.escape(target), case=False, na=False)]

    if matches.empty:
        raise ValueError(f"No row found where '{key_col}' matches '{key_value}'")

    rows = matches.fillna("").astype(str).to_dict(orient="records")
    result: dict[str, Any] = {
        "document_id": document_id,
        "filename": filename,
        "operation": "lookup",
        "key_column": key_col,
        "key_value": key_value,
        "match_count": len(rows),
        "rows": rows,
    }

    if return_column:
        ret_col = _resolve_column(df, return_column)
        result["return_column"] = ret_col
        result["values"] = [row.get(ret_col, "") for row in rows]

    return result


def analyze_spreadsheet(
    db: Session,
    tenant_id: str,
    document_id: str,
    operation: str,
    column: Optional[str] = None,
    match_value: Optional[str] = None,
) -> dict[str, Any]:
    """Run a supported spreadsheet operation. Columns resolved dynamically from the file."""
    df, filename = load_excel_dataframe(db, tenant_id, document_id)
    op = (operation or "columns").strip().lower()

    if op in ("columns", "schema", "headers"):
        return {
            "document_id": document_id,
            "filename": filename,
            "operation": "columns",
            "row_count": int(len(df)),
            "column_count": int(len(df.columns)),
            "columns": [str(c) for c in df.columns],
            "numeric_columns": _numeric_columns(df),
        }

    if op in ("preview", "head", "sample"):
        rows = df.head(5).fillna("").astype(str).to_dict(orient="records")
        return {
            "document_id": document_id,
            "filename": filename,
            "operation": "preview",
            "rows": rows,
        }

    if op in ("sum", "total"):
        _require_column("sum", column, df)
        series, col = _numeric_series(df, column or "")
        return {
            "document_id": document_id,
            "filename": filename,
            "operation": "sum",
            "column": col,
            "value": round(float(series.sum()), 2),
            "rows_used": int(series.notna().sum()),
        }

    if op == "mean":
        _require_column("mean", column, df)
        series, col = _numeric_series(df, column or "")
        return {
            "document_id": document_id,
            "filename": filename,
            "operation": "mean",
            "column": col,
            "value": round(float(series.mean()), 2),
            "rows_used": int(series.notna().sum()),
        }

    if op == "count":
        if column and match_value:
            col, matches = _filter_rows_by_value(df, column, match_value)
            return {
                "document_id": document_id,
                "filename": filename,
                "operation": "count",
                "column": col,
                "match_value": match_value,
                "value": int(len(matches)),
            }
        if column:
            col = _resolve_column(df, column)
            value = int(df[col].notna().sum())
            return {
                "document_id": document_id,
                "filename": filename,
                "operation": "count",
                "column": col,
                "value": value,
            }
        return {
            "document_id": document_id,
            "filename": filename,
            "operation": "count",
            "value": int(len(df)),
        }

    if op in ("min", "max"):
        _require_column(op, column, df)
        series, col = _numeric_series(df, column or "")
        value = float(series.min() if op == "min" else series.max())
        return {
            "document_id": document_id,
            "filename": filename,
            "operation": op,
            "column": col,
            "value": round(value, 2),
            "rows_used": int(series.notna().sum()),
        }

    if op == "describe":
        coerced = {}
        for col in df.columns:
            series = pd.to_numeric(df[col], errors="coerce")
            if series.notna().any():
                coerced[str(col)] = series
        if not coerced:
            raise ValueError(
                "No numeric columns found for describe. "
                "Use operation=columns and preview for text-only spreadsheets."
            )
        numeric = pd.DataFrame(coerced)
        return {
            "document_id": document_id,
            "filename": filename,
            "operation": "describe",
            "summary": numeric.describe().round(2).to_dict(),
        }

    if op in ("nunique", "distinct", "unique_count"):
        _require_column("nunique", column, df)
        col = _resolve_column(df, column or "")
        value = int(df[col].dropna().astype(str).str.strip().nunique())
        return {
            "document_id": document_id,
            "filename": filename,
            "operation": "nunique",
            "column": col,
            "value": value,
            "rows_used": int(df[col].notna().sum()),
        }

    if op in ("value_counts", "counts"):
        _require_column("value_counts", column, df)
        col = _resolve_column(df, column or "")
        counts = (
            df[col]
            .dropna()
            .astype(str)
            .str.strip()
            .value_counts()
            .to_dict()
        )
        return {
            "document_id": document_id,
            "filename": filename,
            "operation": "value_counts",
            "column": col,
            "counts": {str(k): int(v) for k, v in counts.items()},
        }

    if op == "lookup":
        raise ValueError(
            "Use lookup_spreadsheet_row with key_column, key_value, and optional return_column. "
            f"Available columns: {', '.join(str(c) for c in df.columns)}"
        )

    raise ValueError(
        "Unsupported operation. Use one of: columns, preview, sum, mean, count, min, max, "
        "describe, nunique, value_counts, lookup"
    )
