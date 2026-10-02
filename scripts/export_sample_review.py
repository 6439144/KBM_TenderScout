"""
Exports classified tenders from SQLite state store into a formatted markdown review document.
Produces the 30-tender review sample for Milestone 3 human checkpoint.
"""

import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.pipeline.state_store import StateStore

if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

def export_sample():
    store = StateStore()
    tenders = store.get_all_tenders()

    lines = [
        "# Sample of Classified Tenders (Milestone 3 Checkpoint)",
        "",
        "**Product Owner:** Khaled Abed, Digital Solutions Lead, KBM Kuwait  ",
        f"**Sample Size:** {len(tenders)} Canonical Tenders  ",
        "**Status:** ⛔ Human Checkpoint — Pending Owner Review  ",
        "",
        "---",
        "",
        "## Summary Metrics",
        "",
    ]

    stats = store.get_stats()
    lines.append(f"- **Total Canonical Records:** {stats['total_canonical_tenders']}")
    lines.append(f"- **Total Raw Notices Persisted:** {stats['total_raw_notices']}")
    lines.append(f"- **Lifecycle Status Breakdown:** `{stats['by_status']}`")
    lines.append(f"- **Sector Distribution:** `{stats['by_sector']}`")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## Detailed Tender Classification Sample")
    lines.append("")
    lines.append("| # | Tender No | Portal | Canonical Client | Sector | Closing Date | Fee / Bond | ICT Relevant? | Status | Review Needed? |")
    lines.append("|:---|:---|:---|:---|:---|:---|:---|:---|:---|:---|")

    needs_review_items = []

    for idx, t in enumerate(tenders, start=1):
        portals = ", ".join(set(s.portal for s in t.sources))
        rev_flag = "⚠️ YES" if t.needs_review else "✅ NO"
        rel_flag = f"🎯 YES (`{', '.join(t.relevance_keywords[:2])}`)" if t.is_kbm_relevant and t.relevance_keywords else ("🎯 YES" if t.is_kbm_relevant else "NO")
        fee_bond = f"{t.document_fee or '-'} / {t.bid_bond or '-'}"
        client_display = t.client[:35]

        lines.append(
            f"| {idx} | **{t.tender_no}** | `{portals}` | {client_display} | `{t.sector}` | {t.closing_date or '-'} | {fee_bond} | {rel_flag} | `{t.status.value}` | {rev_flag} |"
        )

        if t.needs_review:
            needs_review_items.append((idx, t))

    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 'Needs Review' Audit Queue (FR-6 & FR-8)")
    lines.append("")
    lines.append("The following tenders were automatically flagged for human review (zero silent misclassification):")
    lines.append("")

    for idx, t in needs_review_items:
        lines.append(f"### Tender #{idx}: `{t.tender_no}` ({t.sources[0].portal if t.sources else 'N/A'})")
        lines.append(f"- **Title:** {t.title_ar}")
        lines.append(f"- **Client Raw:** `{t.client_raw}` -> Canonical: `{t.client}`")
        lines.append(f"- **Confidence:** `{t.classification_confidence}`")
        lines.append(f"- **Review Reasons:** `{', '.join(t.review_reasons)}`")
        if t.changes:
            lines.append(f"- **Changes Recorded:** `{t.changes}`")
        lines.append("")

    out_path = Path("docs/SAMPLE_30_CLASSIFIED_TENDERS.md")
    out_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"Exported {len(tenders)} tenders to {out_path}")

if __name__ == "__main__":
    export_sample()
