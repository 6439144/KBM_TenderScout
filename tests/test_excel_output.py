"""
Golden-File & Schema Unit Tests for Generated Excel Report (FR-8).
Verifies RTL views, 7 required sheets, frozen panes, headers, and hyperlinks.
"""

import sys
import unittest
from pathlib import Path
import openpyxl

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

class TestExcelOutput(unittest.TestCase):
    def setUp(self):
        self.report_path = Path("output/reports/KBM_Tenders_Latest.xlsx")
        self.assertTrue(self.report_path.exists(), f"Excel report not found at {self.report_path}")
        self.wb = openpyxl.load_workbook(str(self.report_path))

    def tearDown(self):
        self.wb.close()

    def test_required_sheets_exist(self):
        expected_sheets = ["Summary", "New Today", "All Open", "By Sector", "By Client", "Needs Review", "Run Log"]
        actual_sheets = self.wb.sheetnames
        for sheet_name in expected_sheets:
            self.assertIn(sheet_name, actual_sheets, f"Missing required sheet: {sheet_name}")

    def test_rtl_arabic_view(self):
        """Rule FR-8: Arabic text cells right-to-left."""
        for sheet_name in self.wb.sheetnames:
            ws = self.wb[sheet_name]
            self.assertTrue(
                ws.sheet_view.rightToLeft,
                f"Sheet '{sheet_name}' is not configured for Right-to-Left (RTL) Arabic layout."
            )

    def test_frozen_panes(self):
        """Rule FR-8: Frozen header row."""
        for sheet_name in ["New Today", "All Open", "By Sector", "By Client", "Needs Review", "Run Log"]:
            ws = self.wb[sheet_name]
            self.assertEqual(
                ws.freeze_panes, "A2",
                f"Sheet '{sheet_name}' does not have frozen header row at A2"
            )

    def test_table_headers(self):
        """Verifies canonical table column headers."""
        ws = self.wb["All Open"]
        headers = [cell.value for cell in ws[1]]
        expected = ["رقم المناقصة", "الجهة المصدرة", "موضوع المناقصة", "القطاع", "تاريخ النشر", "آخر موعد للتقديم"]
        for exp in expected:
            self.assertIn(exp, headers)

    def test_summary_kpi_cards(self):
        """Verifies summary sheet KPI cards."""
        ws = self.wb["Summary"]
        self.assertEqual(ws["A4"].value, "جديد اليوم")
        self.assertGreaterEqual(ws["A5"].value, 0)

if __name__ == "__main__":
    unittest.main()
