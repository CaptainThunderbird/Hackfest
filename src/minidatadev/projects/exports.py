"""Portable data and report exports."""

from __future__ import annotations

import html
import io
import json
import zipfile
from typing import Any

import pandas as pd


def export_csv(frame: pd.DataFrame) -> bytes:
    return frame.to_csv(index=False).encode("utf-8")


def export_report(
    *,
    dataset_name: str,
    frame: pd.DataFrame,
    messages: list[dict[str, Any]],
    insights: list[dict[str, Any]],
    cleaning_history: list[dict[str, Any]] | None = None,
) -> bytes:
    """Create a self-contained ZIP with cleaned data and an HTML audit report."""

    history = cleaning_history or []
    report = _report_html(dataset_name, frame, messages, insights, history)
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("cleaned-data.csv", export_csv(frame))
        archive.writestr("analysis-report.html", report)
        archive.writestr(
            "manifest.json",
            json.dumps(
                {
                    "dataset": dataset_name,
                    "rows": len(frame),
                    "columns": list(map(str, frame.columns)),
                    "conversation_messages": len(messages),
                    "saved_insights": len(insights),
                    "cleaning_history": history,
                },
                indent=2,
            ),
        )
    return output.getvalue()


def _report_html(
    dataset_name: str,
    frame: pd.DataFrame,
    messages: list[dict[str, Any]],
    insights: list[dict[str, Any]],
    cleaning_history: list[dict[str, Any]],
) -> str:
    conversation = "".join(
        f"<section><strong>{html.escape(str(item.get('role', '')).title())}</strong>"
        f"<p>{html.escape(str(item.get('content', '')))}</p></section>"
        for item in messages
    ) or "<p>No conversation has been saved yet.</p>"
    insight_html = "".join(
        f"<li><strong>{html.escape(str(item.get('title', 'Insight')))}</strong>: "
        f"{html.escape(str(item.get('detail', '')))}</li>"
        for item in insights
    ) or "<li>No saved insights.</li>"
    cleaning_html = "".join(
        "<li>" + html.escape("; ".join(map(str, item.get("actions", [])))) + "</li>"
        for item in cleaning_history
    ) or "<li>No cleaning transformations were applied.</li>"
    return f"""<!doctype html><html><head><meta charset="utf-8">
<title>MiniDataDev report</title><style>
body{{font:16px/1.5 system-ui;max-width:900px;margin:40px auto;padding:0 20px}}
table{{border-collapse:collapse;width:100%}}td,th{{border:1px solid #ddd;padding:7px}}
section{{border-top:1px solid #ddd;padding:12px 0}}small{{color:#667}}
</style></head><body><h1>{html.escape(dataset_name)}</h1>
<p><small>Exported from MiniDataDev · {len(frame):,} rows ·
{len(frame.columns):,} columns</small></p>
<h2>Saved insights</h2><ul>{insight_html}</ul>
<h2>Cleaning history</h2><ol>{cleaning_html}</ol>
<h2>Conversation</h2>{conversation}
<h2>Data preview</h2>{frame.head(100).to_html(index=False, escape=True)}
<p><small>The complete dataset is included as cleaned-data.csv.</small></p>
</body></html>"""
