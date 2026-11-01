import pandas as pd
import plotly.express as px

from app.services.analytics_engine import _validate_dataframe


SUPPORTED_CHART_TYPES = {"bar", "line", "scatter", "histogram", "box", "pie", "heatmap"}
SUPPORTED_AGGREGATIONS = {"sum", "mean", "median", "min", "max", "count"}


def _validate_column(df: pd.DataFrame, column: str | None, label: str, required: bool = True):
    if column is None and not required:
        return
    if column is None:
        raise ValueError(f"{label} column is required.")
    if column not in df.columns:
        raise ValueError(f"Column '{column}' does not exist.")


def recommend_charts(df: pd.DataFrame) -> dict:
    """Suggest chart configurations based on detected column data types."""
    _validate_dataframe(df)

    numeric = [str(c) for c in df.select_dtypes(include="number").columns]
    categorical = [
        str(c) for c in df.select_dtypes(include=["object", "category", "string"]).columns
    ]
    datetime = [str(c) for c in df.select_dtypes(include=["datetime"]).columns]

    recommendations = []

    if categorical and numeric:
        recommendations.append({
            "chart_type": "bar",
            "title": f"{numeric[0]} by {categorical[0]}",
            "x": categorical[0],
            "y": numeric[0],
            "aggregation": "sum",
            "reason": "Compare a numeric metric across categories.",
        })

    if datetime and numeric:
        recommendations.append({
            "chart_type": "line",
            "title": f"{numeric[0]} over time",
            "x": datetime[0],
            "y": numeric[0],
            "aggregation": "sum",
            "reason": "Explore how a numeric metric changes over time.",
        })

    if len(numeric) >= 2:
        recommendations.append({
            "chart_type": "scatter",
            "title": f"{numeric[0]} vs {numeric[1]}",
            "x": numeric[0],
            "y": numeric[1],
            "reason": "Inspect the relationship between two numeric variables.",
        })

    if numeric:
        recommendations.append({
            "chart_type": "histogram",
            "title": f"Distribution of {numeric[0]}",
            "x": numeric[0],
            "reason": "Understand the distribution and spread of a numeric variable.",
        })
        recommendations.append({
            "chart_type": "box",
            "title": f"Spread of {numeric[0]}",
            "x": categorical[0] if categorical else None,
            "y": numeric[0],
            "reason": "Compare spread and identify potential outliers.",
        })

    if categorical:
        recommendations.append({
            "chart_type": "pie",
            "title": f"Composition by {categorical[0]}",
            "x": categorical[0],
            "reason": "Show the share of records across categories.",
        })

    if len(numeric) >= 2:
        recommendations.append({
            "chart_type": "heatmap",
            "title": "Numeric feature correlation",
            "reason": "Show pairwise correlations between numeric columns.",
        })

    return {
        "available_chart_types": sorted(SUPPORTED_CHART_TYPES),
        "numeric_columns": numeric,
        "categorical_columns": categorical,
        "datetime_columns": datetime,
        "recommendations": recommendations,
    }


def build_chart(
    df: pd.DataFrame,
    chart_type: str,
    x: str | None = None,
    y: str | None = None,
    color: str | None = None,
    aggregation: str = "sum",
    max_points: int = 1000,
) -> dict:
    """Build a Plotly chart and return its JSON-serializable figure."""
    _validate_dataframe(df)

    if chart_type not in SUPPORTED_CHART_TYPES:
        raise ValueError(f"Unsupported chart type. Choose from: {sorted(SUPPORTED_CHART_TYPES)}")

    if aggregation not in SUPPORTED_AGGREGATIONS:
        raise ValueError(f"Unsupported aggregation. Choose from: {sorted(SUPPORTED_AGGREGATIONS)}")

    if not isinstance(max_points, int) or isinstance(max_points, bool) or not 1 <= max_points <= 10000:
        raise ValueError("max_points must be an integer between 1 and 10000.")

    _validate_column(df, x, "X", required=chart_type != "heatmap")
    _validate_column(df, y, "Y", required=chart_type in {"bar", "line", "scatter", "box"})
    _validate_column(df, color, "Color", required=False)

    data = df.copy()

    if chart_type in {"bar", "line"}:
        if not pd.api.types.is_numeric_dtype(data[y]):
            raise ValueError("Y column must be numeric for bar and line charts.")
        data = (
            data.groupby(x, dropna=False)[y]
            .agg(aggregation)
            .reset_index()
            .sort_values(x)
        )
        if len(data) > max_points:
            data = data.head(max_points)
        fig = px.bar(data, x=x, y=y, title=f"{aggregation.title()} of {y} by {x}") if chart_type == "bar" else px.line(data, x=x, y=y, title=f"{aggregation.title()} of {y} by {x}")

    elif chart_type == "scatter":
        if not pd.api.types.is_numeric_dtype(data[x]) or not pd.api.types.is_numeric_dtype(data[y]):
            raise ValueError("X and Y columns must be numeric for scatter charts.")
        if len(data) > max_points:
            data = data.sample(n=max_points, random_state=42)
        fig = px.scatter(data, x=x, y=y, color=color, title=f"{y} vs {x}")

    elif chart_type == "histogram":
        if not pd.api.types.is_numeric_dtype(data[x]):
            raise ValueError("X column must be numeric for a histogram.")
        fig = px.histogram(data, x=x, color=color, title=f"Distribution of {x}")

    elif chart_type == "box":
        if not pd.api.types.is_numeric_dtype(data[y]):
            raise ValueError("Y column must be numeric for a box plot.")
        fig = px.box(data, x=x, y=y, color=color, title=f"Distribution of {y}")

    elif chart_type == "pie":
        counts = data[x].astype("string").fillna("Missing").value_counts().head(max_points)
        pie_data = counts.rename_axis(x).reset_index(name="count")
        fig = px.pie(pie_data, names=x, values="count", title=f"Composition by {x}")

    else:  # heatmap
        numeric = data.select_dtypes(include="number")
        if numeric.shape[1] < 2:
            raise ValueError("Heatmap requires at least two numeric columns.")
        correlation = numeric.corr()
        fig = px.imshow(
            correlation,
            text_auto=".2f",
            aspect="auto",
            color_continuous_scale="RdBu_r",
            zmin=-1,
            zmax=1,
            title="Numeric Feature Correlation",
        )

    fig.update_layout(template="plotly_white", margin={"l": 40, "r": 20, "t": 60, "b": 40})

    return {
        "chart_type": chart_type,
        "data_points": int(len(data)),
        "figure": fig.to_dict(),
    }
