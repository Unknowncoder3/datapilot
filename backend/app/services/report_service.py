from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from app.services.analytics_engine import (
    _clean_value,
    get_analytics_overview,
    get_descriptive_statistics,
    get_correlation_matrix,
)
from app.services.profiler import profile_dataframe, read_dataset


def build_report_content(dataset_path: Path, report_type: str = "summary") -> dict:
    """Build a JSON-safe, dataset-grounded report from an uploaded file."""
    if report_type not in {"summary", "full", "executive"}:
        raise ValueError("Report type must be 'summary', 'full', or 'executive'.")

    path = Path(dataset_path).resolve()
    if not path.is_file():
        raise FileNotFoundError("Dataset file is missing from storage.")

    df = read_dataset(path)
    if df.empty or len(df.columns) == 0:
        raise ValueError("Cannot generate a report from an empty dataset.")

    profile = profile_dataframe(df)
    content = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "report_type": report_type,
        "overview": get_analytics_overview(df),
        "data_quality": {
            "quality_score": profile["quality_score"],
            "row_count": profile["row_count"],
            "column_count": profile["column_count"],
            "missing_cells": profile["missing_cells"],
            "duplicate_rows": profile["duplicate_rows"],
            "columns": profile["columns"],
        },
        "descriptive_statistics": get_descriptive_statistics(df),
    }

    if report_type == "executive":
        content["executive_analysis"] = _build_executive_analysis(df.copy())

    if report_type == "full":
        content["correlation"] = get_correlation_matrix(df)
        sample = df.head(20)
        content["sample_rows"] = [
            {str(column): _clean_value(value) for column, value in row.items()}
            for row in sample.to_dict(orient="records")
        ]
        content["sample_row_count"] = len(sample)

    return content


def _build_executive_analysis(df: pd.DataFrame) -> dict:
    """Create a management-facing, dataset-grounded business analysis."""
    rows = len(df)
    date_col = next((c for c in df.columns if pd.api.types.is_datetime64_any_dtype(df[c])), None)
    if date_col is None:
        for c in df.columns:
            if any(token in str(c).lower() for token in ("date", "time", "month", "period")):
                parsed = pd.to_datetime(df[c], errors="coerce")
                if parsed.notna().mean() >= 0.7:
                    df[ c ] = parsed
                    date_col = c
                    break

    numeric = [c for c in df.select_dtypes(include="number").columns if df[c].nunique(dropna=True)>1]
    measure = next((c for c in numeric if any(t in str(c).lower() for t in ("revenue","sales","amount","turnover","total","profit","value"))), None)
    measure_label = str(measure) if measure is not None else None
    metric_series = df[measure].astype(float) if measure is not None else None
    metric_formula = None
    if measure is None:
        qty = next((c for c in numeric if any(t in str(c).lower() for t in ("quantity","units","volume"))), None)
        price = next((c for c in numeric if any(t in str(c).lower() for t in ("unitprice","price","rate"))), None)
        if qty is not None and price is not None:
            metric_series = df[qty].astype(float) * df[price].astype(float)
            measure_label = f"{qty} × {price}"
            metric_formula = f"{qty} multiplied by {price}"
        elif numeric:
            measure = next((c for c in numeric if any(t in str(c).lower() for t in ("quantity","units","volume"))), numeric[0])
            metric_series = df[measure].astype(float)
            measure_label = str(measure)
    if metric_series is not None:
        metric_series = metric_series.replace([float("inf"), float("-inf")], pd.NA)
        total = float(metric_series.sum(skipna=True))
        average = float(metric_series.mean()) if metric_series.notna().any() else 0.0
        median = float(metric_series.median()) if metric_series.notna().any() else 0.0
        positive = int((metric_series > 0).sum())
        negative = int((metric_series < 0).sum())
    else:
        total = average = median = 0.0
        positive = negative = 0

    kpis = [
        {"label":"Records analyzed","value":rows,"format":"count"},
        {"label":f"Total {measure_label or 'observations'}","value":_clean_value(total),"format":"metric","metric":measure_label},
        {"label":f"Average {measure_label or 'value'} per record","value":_clean_value(average),"format":"metric","metric":measure_label},
        {"label":"Positive records","value":positive,"format":"count"},
        {"label":"Negative records","value":negative,"format":"count"},
    ]
    trend=[]
    change=None
    peak=None
    trough=None
    if date_col is not None and metric_series is not None:
        frame=pd.DataFrame({"date":pd.to_datetime(df[date_col],errors="coerce"),"metric":metric_series}).dropna()
        if not frame.empty:
            frame["period"]=frame["date"].dt.to_period("M").astype(str)
            grouped=frame.groupby("period",sort=True)["metric"].sum()
            trend=[{"period":str(period),"value":_clean_value(value)} for period,value in grouped.items()]
            if len(grouped)>=2:
                prior=float(grouped.iloc[-2]); latest=float(grouped.iloc[-1])
                change={"period":str(grouped.index[-1]),"previous_period":str(grouped.index[-2]),"current_value":_clean_value(latest),"previous_value":_clean_value(prior),"absolute_change":_clean_value(latest-prior),"percentage_change":_clean_value(((latest-prior)/abs(prior)*100) if prior else None),"direction":"up" if latest>prior else "down" if latest<prior else "flat"}
                latest_period=frame["date"].max().to_period("M")
                latest_cutoff=int(frame.loc[frame["date"].dt.to_period("M")==latest_period,"date"].dt.day.max())
                latest_month_end=latest_period.days_in_month
                partial=latest_cutoff<latest_month_end
                previous_period=latest_period-1
                current_slice=frame[(frame["date"].dt.to_period("M")==latest_period)&(frame["date"].dt.day<=latest_cutoff)]
                previous_slice=frame[(frame["date"].dt.to_period("M")==previous_period)&(frame["date"].dt.day<=latest_cutoff)]
                current_lfl=float(current_slice["metric"].sum())
                previous_lfl=float(previous_slice["metric"].sum())
                lfl_delta=current_lfl-previous_lfl
                change["like_for_like"]={"period":str(latest_period),"previous_period":str(previous_period),"cutoff_day":latest_cutoff,"current_value":_clean_value(current_lfl),"previous_value":_clean_value(previous_lfl),"absolute_change":_clean_value(lfl_delta),"percentage_change":_clean_value((lfl_delta/abs(previous_lfl)*100) if previous_lfl else None),"direction":"up" if lfl_delta>0 else "down" if lfl_delta<0 else "flat","partial_period":partial,"warning":f"{latest_period} data is observed only through day {latest_cutoff}; the comparison uses days 1–{latest_cutoff} for both periods." if partial else "The latest period appears complete based on the observed maximum date."}
            if not grouped.empty:
                peak={"period":str(grouped.idxmax()),"value":_clean_value(grouped.max())}
                trough={"period":str(grouped.idxmin()),"value":_clean_value(grouped.min())}

    breakdowns=[]
    dimensions=[c for c in df.columns if c!=date_col and c!=measure and (pd.api.types.is_object_dtype(df[c]) or pd.api.types.is_string_dtype(df[c]) or isinstance(df[c].dtype, pd.CategoricalDtype)) and 2<=df[c].nunique(dropna=True)<=100]
    if metric_series is not None:
        for column in dimensions[:4]:
            temp=pd.DataFrame({"dimension":df[column].astype("string").fillna("Unknown"),"metric":metric_series})
            agg=temp.groupby("dimension",dropna=False)["metric"].sum().sort_values(ascending=False).head(8)
            breakdowns.append({"dimension":str(column),"leaders":[{"name":str(name),"value":_clean_value(value),"contribution_pct":_clean_value((float(value)/total*100) if total else None)} for name,value in agg.items()]})

    observations=[]
    if change:
        pct=change.get("percentage_change")
        pct_text = f"{float(pct):+,.2f}%" if pct is not None else "N/A"
        absolute_text = f"{float(change['absolute_change']):+,.2f}"
        movement_word = "increased" if change["direction"] == "up" else "decreased" if change["direction"] == "down" else "was unchanged"
        detail=f"From {change['previous_period']} to {change['period']}, the metric {movement_word} by {pct_text} ({absolute_text} in absolute terms)."
        comparable=change.get("like_for_like")
        if comparable and comparable.get("partial_period"):
            comparable_pct=comparable.get("percentage_change")
            comparable_text=f"{float(comparable_pct):+,.2f}%" if comparable_pct is not None else "N/A"
            detail += f" However, {change['period']} is incomplete (data through day {comparable['cutoff_day']}); comparing days 1–{comparable['cutoff_day']} across both months shows {comparable['direction']} movement of {comparable_text}."
        observations.append({"title":f"Period-over-period movement: {change['direction']}","detail":detail})
    if peak:
        observations.append({"title":"Peak period","detail":f"The highest monthly {measure_label or 'metric'} was {float(peak['value']):,.2f} in {peak['period']}."})
    if trough:
        observations.append({"title":"Lowest period","detail":f"The lowest monthly {measure_label or 'metric'} was {float(trough['value']):,.2f} in {trough['period']}."})
    for item in breakdowns[:3]:
        if item["leaders"]:
            leader=item["leaders"][0]
            observations.append({"title":f"Leading {item['dimension']}","detail":f"{leader['name']} leads this breakdown with {leader['value']} for {measure_label or 'the selected metric'}."})
    if not observations:
        observations.append({"title":"Trend analysis unavailable","detail":"The dataset does not contain a sufficiently reliable date field and business measure for time-based comparisons. Review field mapping to enable trend reporting."})

    recommendations=[]
    comparable_direction=change.get("like_for_like",{}).get("direction") if change and change.get("like_for_like",{}).get("partial_period") else (change["direction"] if change else None)
    if comparable_direction=="down":
        recommendations.append("Investigate the comparable-period decline by segment, product, geography, and customer cohort; validate whether the movement is seasonal or operational.")
    elif comparable_direction=="up":
        recommendations.append("Validate the comparable-period growth drivers and assess whether the strongest segments can be scaled sustainably.")
    if breakdowns and breakdowns[0]["leaders"]:
        recommendations.append(f"Review the concentration in the leading {breakdowns[0]['dimension']} segment and compare its performance with lower-ranked segments.")
    recommendations.append("Confirm metric definitions and data completeness before using this report for financial or operational decisions.")

    return {
        "report_title":"Executive Business Performance Report",
        "executive_summary": observations[0]["detail"],
        "metric_name":measure_label,
        "metric_formula":metric_formula,
        "kpis":kpis,
        "trend":{"date_field":str(date_col) if date_col is not None else None,"metric":measure_label,"granularity":"monthly","series":trend,"period_change":change,"peak_period":peak,"lowest_period":trough},
        "performance_breakdowns":breakdowns,
        "key_findings":observations,
        "management_recommendations":recommendations,
        "analysis_notes":[
            "Findings are calculated from the uploaded dataset; they are descriptive and do not establish causation.",
            "Where a business value is derived, the formula is shown explicitly.",
            "A date trend is shown only when a date field could be parsed with reasonable confidence.",
            *([change["like_for_like"]["warning"]+" Period-over-period headline values remain raw monthly totals; use the like-for-like comparison for a more comparable read." ] if change and change.get("like_for_like") and change["like_for_like"]["partial_period"] else [])
        ]
    }

