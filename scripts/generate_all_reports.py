import sys
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import load_config
from src.pipeline.state_store import StateStore
from src.output.excel import ExcelReportGenerator
from src.output.html_dashboard import generate_standalone_dashboard

def main():
    config = load_config()
    state_store = StateStore()
    
    # 1. Excel Report
    excel_gen = ExcelReportGenerator(config=config.excel, state_store=state_store)
    report_path = excel_gen.generate_report()
    print(f"Generated Excel report at: {report_path}")

    # 2. Standalone HTML Dashboard
    dash_path = generate_standalone_dashboard()
    print(f"Generated Standalone HTML Dashboard at: {dash_path}")

if __name__ == "__main__":
    main()
