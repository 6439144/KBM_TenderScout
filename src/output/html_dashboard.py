"""
KBM Tender Scout - Standalone Interactive HTML Dashboard Generator
Generates a zero-dependency, single-file HTML report containing the complete
tender database, KBM profile qualification scores, filters, and analytics.
Can be opened directly in any browser (Chrome, Edge, Firefox) by double-clicking.
"""

import json
import sys
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.pipeline.state_store import StateStore
from src.pipeline.kbm_qualifier import KBM_BUSINESS_UNITS

def generate_standalone_dashboard(output_path: Path = None) -> Path:
    state_store = StateStore()
    tenders = state_store.get_all_tenders()
    
    tenders_dict = [t.model_dump() for t in tenders]
    # Sort descending by KBM fit score
    tenders_dict.sort(key=lambda x: (x.get("kbm_fit_score", 0), x.get("publish_date") or ""), reverse=True)
    
    total = len(tenders)
    high_priority = sum(1 for t in tenders if t.kbm_fit_score >= 70.0)
    target_opps = sum(1 for t in tenders if 40.0 <= t.kbm_fit_score < 70.0)
    unrelated = sum(1 for t in tenders if t.kbm_fit_score < 40.0)
    
    by_bu = {}
    for bu_name in KBM_BUSINESS_UNITS.keys():
        by_bu[bu_name] = sum(1 for t in tenders if t.kbm_bu == bu_name)

    stats = {
        "total_tenders": total,
        "high_priority_bids": high_priority,
        "target_opportunities": target_opps,
        "unrelated": unrelated,
        "closing_soon": sum(1 for t in tenders if t.closing_date),
        "by_bu": by_bu
    }

    template_path = Path(__file__).resolve().parent.parent / "web" / "templates" / "index.html"
    template_html = template_path.read_text(encoding="utf-8")

    # Inject embedded data directly into the HTML
    embedded_script = f"""
    <!-- EMBEDDED OFFLINE DATA -->
    <script>
      window.EMBEDDED_TENDERS = {json.dumps(tenders_dict, ensure_ascii=False)};
      window.EMBEDDED_STATS = {json.dumps(stats, ensure_ascii=False)};
    </script>
    """

    # Modify the fetch functions in template so if window.EMBEDDED_TENDERS is present, it uses that instead of network fetch
    offline_adapter = """
    // Offline Data Adapter
    const originalFetchStats = fetchStats;
    fetchStats = async function() {
      if (window.EMBEDDED_STATS) {
        const data = window.EMBEDDED_STATS;
        document.getElementById('stat-total').innerText = data.total_tenders;
        document.getElementById('stat-high').innerText = data.high_priority_bids;
        document.getElementById('stat-target').innerText = data.target_opportunities;
        document.getElementById('stat-closing').innerText = data.closing_soon;
        if (data.by_bu) {
          document.getElementById('bu-count-systems').innerText = data.by_bu['IBM BU - Systems'] || 0;
          document.getElementById('bu-count-solutions').innerText = data.by_bu['IBM BU - Solutions & Channel'] || 0;
          document.getElementById('bu-count-cloud').innerText = data.by_bu['Cloud BU'] || 0;
          document.getElementById('bu-count-security').innerText = data.by_bu['Security BU'] || 0;
          document.getElementById('bu-count-services').innerText = data.by_bu['Services BU (MOPS)'] || 0;
        }
        return;
      }
      return originalFetchStats();
    };

    const originalFetchTenders = fetchTenders;
    fetchTenders = async function() {
      if (window.EMBEDDED_TENDERS) {
        allTenders = window.EMBEDDED_TENDERS;
        renderTenders(allTenders);
        return;
      }
      return originalFetchTenders();
    };
    """

    # Insert embedded script before closing head
    standalone_html = template_html.replace("</head>", f"{embedded_script}\n</head>")
    # Insert adapter into script
    standalone_html = standalone_html.replace("// Initialize application", f"{offline_adapter}\n    // Initialize application")

    if output_path is None:
        output_dir = Path(__file__).resolve().parent.parent.parent / "output" / "reports"
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / "KBM_Tender_Dashboard.html"

    output_path.write_text(standalone_html, encoding="utf-8")
    return output_path

if __name__ == "__main__":
    path = generate_standalone_dashboard()
    print(f"Generated standalone dashboard at: {path}")
