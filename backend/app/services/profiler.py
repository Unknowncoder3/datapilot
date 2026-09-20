from pathlib import Path
import pandas as pd

def read_dataset(path: Path):
    suffix = path.suffix.lower()
    if suffix == ".csv":
        return pd.read_csv(path)
    if suffix in {".xlsx", ".xls"}:
        return pd.read_excel(path)
    raise ValueError(f"Unsupported file type: {suffix}")

def infer_semantic_type(series):
    if pd.api.types.is_datetime64_any_dtype(series): return "datetime"
    if pd.api.types.is_bool_dtype(series): return "boolean"
    if pd.api.types.is_numeric_dtype(series): return "numeric"
    return "categorical"

def profile_dataframe(df):
    columns=[]
    for name in df.columns:
        s=df[name]
        columns.append({"name":str(name),"dtype":str(s.dtype),"semantic_type":infer_semantic_type(s),"missing":int(s.isna().sum()),"unique":int(s.nunique(dropna=True)),"sample_values":[str(v) for v in s.dropna().head(5).tolist()]})
    return {"row_count":int(len(df)),"column_count":int(len(df.columns)),"missing_cells":int(df.isna().sum().sum()),"duplicate_rows":int(df.duplicated().sum()),"columns":columns}
