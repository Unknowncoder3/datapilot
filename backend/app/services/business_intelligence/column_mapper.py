import re
from typing import Any

import pandas as pd

from app.services.analytics_engine import _validate_dataframe


ROLE_ALIASES = {
    "date": {"date", "datetime", "timestamp", "orderdate", "invoicedate", "transactiondate", "createdat", "purchase_date"},
    "customer_id": {"customerid", "customer_id", "clientid", "buyerid", "user_id", "userid"},
    "order_id": {"orderid", "order_id", "invoice", "invoiceno", "transactionid", "receiptid", "purchaseid"},
    "product_id": {"productid", "product_id", "itemid", "sku", "stockcode", "variantid"},
    "product_name": {"product", "productname", "product_name", "item", "itemname", "description", "title"},
    "category": {"category", "productcategory", "product_category", "itemcategory", "department", "segment"},
    "quantity": {"quantity", "qty", "units", "unitssold", "itemquantity", "count"},
    "unit_price": {"unitprice", "unit_price", "price", "sellingprice", "saleprice", "itemprice"},
    "revenue": {"revenue", "sales", "salesamount", "totalamount", "ordertotal", "linetotal", "amount", "turnover"},
    "cost": {"cost", "unitcost", "unit_cost", "costprice", "purchasecost", "cogs"},
    "profit": {"profit", "grossprofit", "netprofit", "profitamount", "marginamount"},
    "country": {"country", "nation"},
    "region": {"region", "state", "province", "territory", "city", "market"},
}

NUMERIC_ROLES = {"quantity", "unit_price", "revenue", "cost", "profit"}
IDENTIFIER_TOKENS = {
    "customer_id": ("customer", "client", "buyer", "user"),
    "order_id": ("order", "invoice", "transaction", "receipt", "purchase"),
    "product_id": ("product", "item", "sku", "stock", "variant"),
}


def _normalize_name(value: Any) -> str:
    return re.sub(r"[^a-z0-9]", "", str(value).strip().lower())


def _candidate_score(column: str, role: str, series: pd.Series) -> tuple[int, str | None]:
    normalized = _normalize_name(column)

    # Exclude date/time fields before alias matching. For example, InvoiceDate
    # must not match the "invoice" prefix used by the order_id role.
    if role in IDENTIFIER_TOKENS and any(
        token in normalized for token in ("date", "time", "timestamp")
    ):
        return 0, None

    aliases = {_normalize_name(alias) for alias in ROLE_ALIASES[role]}

    if normalized in aliases:
        return 100, "Column name exactly matches a known business field."

    for alias in aliases:
        if alias and (normalized.startswith(alias) or normalized.endswith(alias)):
            return 85, "Column name contains a known business-field name."

    if role == "date" and pd.api.types.is_datetime64_any_dtype(series):
        return 70, "Column has a datetime data type."
    if role in NUMERIC_ROLES and pd.api.types.is_numeric_dtype(series):
        return 15, "Column is numeric; confirm its business meaning manually."
    if role in IDENTIFIER_TOKENS:
        if any(token in normalized for token in IDENTIFIER_TOKENS[role]):
            return 65, "Column name suggests this type of identifier."
    if role in {"product_name", "category", "country", "region"}:
        if role == "region" and normalized in {"state", "province", "city", "territory", "market"}:
            return 80, "Column name suggests a geographic grouping."
    return 0, None


def map_business_columns(df: pd.DataFrame) -> dict:
    """Infer likely business fields from column names and data types."""
    _validate_dataframe(df)

    candidates = {}
    mapping = {}
    warnings = []

    for role, aliases in ROLE_ALIASES.items():
        role_candidates = []
        for column in df.columns:
            score, reason = _candidate_score(str(column), role, df[column])
            if score:
                role_candidates.append({
                    "column": str(column),
                    "confidence": "high" if score >= 85 else "medium" if score >= 60 else "low",
                    "score": score,
                    "reason": reason,
                })
        role_candidates.sort(key=lambda item: item["score"], reverse=True)
        candidates[role] = role_candidates

        strong = [item for item in role_candidates if item["score"] >= 60]
        if len(strong) == 1:
            mapping[role] = strong[0]["column"]
        elif len(strong) > 1:
            warnings.append(
                f"Multiple possible columns found for '{role}'; choose the correct one."
            )
            mapping[role] = None
        else:
            mapping[role] = None

    if mapping["revenue"] is None and mapping["quantity"] and mapping["unit_price"]:
        mapping["revenue"] = {
            "type": "derived",
            "formula": "quantity * unit_price",
            "depends_on": [mapping["quantity"], mapping["unit_price"]],
        }

    if mapping["date"] is None:
        warnings.append("No transaction date column was confidently detected.")
    if mapping["customer_id"] is None:
        warnings.append("Customer-level analysis requires a customer identifier.")
    if mapping["order_id"] is None:
        warnings.append("Order-level KPIs require an order or invoice identifier.")
    if mapping["revenue"] is None:
        warnings.append("Revenue could not be detected or derived from quantity and unit price.")

    return {
        "mapping": mapping,
        "candidates": candidates,
        "available_columns": [str(column) for column in df.columns],
        "warnings": warnings,
    }


def validate_business_mapping(df: pd.DataFrame, mapping: dict) -> dict:
    """Validate user-supplied business role to dataset-column mappings."""
    _validate_dataframe(df)

    if not isinstance(mapping, dict):
        raise ValueError("Mapping must be a JSON object of business roles to column names.")

    unknown_roles = sorted(set(mapping) - set(ROLE_ALIASES))
    if unknown_roles:
        raise ValueError(f"Unsupported business roles: {unknown_roles}")

    validated = {}
    for role, column in mapping.items():
        if column is None:
            validated[role] = None
            continue
        if not isinstance(column, str) or column not in df.columns:
            raise ValueError(f"Invalid column for '{role}': {column!r}.")
        if role in NUMERIC_ROLES and not pd.api.types.is_numeric_dtype(df[column]):
            raise ValueError(f"Column '{column}' must be numeric for role '{role}'.")
        if role == "date" and not (
            pd.api.types.is_datetime64_any_dtype(df[column])
            or any(token in _normalize_name(column) for token in ("date", "time", "timestamp"))
        ):
            raise ValueError(f"Column '{column}' does not appear to be a date/time field.")
        validated[role] = column

    return {
        "mapping": validated,
        "validated": True,
        "note": "Mapping validated for this request; it is not persisted to the dataset.",
    }
