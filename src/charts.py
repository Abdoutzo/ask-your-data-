"""Chart suggestion and rendering.

suggest() is a deterministic heuristic over the result shape — no LLM
needed, which means it's testable. render() builds a Plotly figure the
Streamlit app can display.
"""
import re
from dataclasses import dataclass
from typing import Any, Dict, List

from src.execute import Result

DATE_LIKE = re.compile(r"^\d{4}(-\d{2})?(-\d{2})?$")


@dataclass
class ChartSpec:
    kind: str  # 'line' | 'bar' | 'table'
    x: str = ""
    y: str = ""
    title: str = ""


def _looks_like_date(values: List[Any]) -> bool:
    vals = [str(v) for v in values if v is not None][:20]
    return bool(vals) and all(DATE_LIKE.match(v) for v in vals)


def _is_numeric(values: List[Any]) -> bool:
    vals = [v for v in values if v is not None][:20]
    return bool(vals) and all(isinstance(v, (int, float)) for v in vals)


def suggest(result: Result) -> ChartSpec:
    """Pick a chart from the shape of the data."""
    if result.n_rows == 0 or len(result.columns) < 2:
        return ChartSpec(kind="table")
    x_col, y_col = result.columns[0], result.columns[1]
    x_vals = result.col_values(x_col)
    y_vals = result.col_values(y_col)
    if _looks_like_date(x_vals) and _is_numeric(y_vals):
        return ChartSpec(kind="line", x=x_col, y=y_col,
                         title=f"{y_col} par {x_col}")
    if _is_numeric(y_vals) and result.n_rows <= 15:
        return ChartSpec(kind="bar", x=x_col, y=y_col,
                         title=f"{y_col} par {x_col}")
    return ChartSpec(kind="table")


def render(result: Result, spec: ChartSpec):
    """Build a Plotly figure (or None for table)."""
    if spec.kind == "table":
        return None
    import plotly.express as px
    data = {c: result.col_values(c) for c in result.columns[:2]}
    if spec.kind == "line":
        fig = px.line(data, x=spec.x, y=spec.y, title=spec.title,
                      markers=True)
    else:
        fig = px.bar(data, x=spec.x, y=spec.y, title=spec.title)
    fig.update_layout(margin=dict(l=20, r=20, t=40, b=20), height=380)
    return fig


def to_display_rows(result: Result, limit: int = 20) -> List[Dict[str, Any]]:
    return result.rows[:limit]
