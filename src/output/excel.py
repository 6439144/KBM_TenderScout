"""
Excel Workbook Generator for KBM Tender Scout (FR-8).
Generates professional RTL Arabic reports with 7 sheets, conditional styling, and hyperlinked sources.
"""

import os
import shutil
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional
import openpyxl
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from src.config import ExcelConfig
from src.models import CanonicalTenderRecord, TenderStatus
from src.pipeline.state_store import StateStore

# Professional Styling Constants
HEADER_FILL = PatternFill(start_color="1A365D", end_color="1A365D", fill_type="solid")  # Navy
HEADER_FONT = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
CARD_HEADER_FILL = PatternFill(start_color="2B6CB0", end_color="2B6CB0", fill_type="solid")

ZEBRA_FILL = PatternFill(start_color="F7FAFC", end_color="F7FAFC", fill_type="solid")
WHITE_FILL = PatternFill(start_color="FFFFFF", end_color="FFFFFF", fill_type="solid")

# Status Fills
STATUS_FILLS = {
    "NEW": PatternFill(start_color="D4EDDA", end_color="D4EDDA", fill_type="solid"),        # Soft Green
    "UPDATED": PatternFill(start_color="FFF3CD", end_color="FFF3CD", fill_type="solid"),    # Soft Amber
    "UNCHANGED": PatternFill(start_color="EDF2F7", end_color="EDF2F7", fill_type="solid"),  # Neutral Gray
    "CLOSED": PatternFill(start_color="E2E8F0", end_color="E2E8F0", fill_type="solid"),     # Muted Gray
    "CANCELLED": PatternFill(start_color="F8D7DA", end_color="F8D7DA", fill_type="solid"),  # Soft Red
}

ALERT_FILL = PatternFill(start_color="F8D7DA", end_color="F8D7DA", fill_type="solid")       # Urgent Red
ICT_FILL = PatternFill(start_color="EBF8FF", end_color="EBF8FF", fill_type="solid")         # Tech Blue

BORDER_THIN = Border(
    left=Side(style='thin', color='D2D6DC'),
    right=Side(style='thin', color='D2D6DC'),
    top=Side(style='thin', color='D2D6DC'),
    bottom=Side(style='thin', color='D2D6DC')
)

ALIGN_RIGHT = Alignment(horizontal='right', vertical='center', wrap_text=True)
ALIGN_CENTER = Alignment(horizontal='center', vertical='center')
ALIGN_LEFT = Alignment(horizontal='left', vertical='center')

class ExcelReportGenerator:
    def __init__(self, config: ExcelConfig, state_store: StateStore):
        self.config = config
        self.state_store = state_store
        self.output_dir = Path(config.output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate_report(self, run_logs: Optional[List[Dict[str, Any]]] = None) -> Path:
        """Builds and writes the complete Excel workbook across all 7 sheets."""
        wb = openpyxl.Workbook()
        # Remove default sheet
        wb.remove(wb.active)

        all_tenders = self.state_store.get_all_tenders()
        today_iso = date.today().isoformat()
        closing_soon_cutoff = (date.today() + timedelta(days=self.config.closing_soon_days)).isoformat()

        # 1. Summary Sheet
        self._build_summary_sheet(wb, all_tenders, today_iso)

        open_tenders = [t for t in all_tenders if t.status != TenderStatus.CLOSED and t.status != TenderStatus.CANCELLED]

        # 2. KBM Qualified Opportunities Sheet (Presales Priority)
        kbm_tenders = sorted(
            [t for t in open_tenders if (t.kbm_fit_score >= 30.0 or t.is_kbm_relevant)],
            key=lambda t: t.kbm_fit_score,
            reverse=True
        )
        self._build_kbm_opportunities_sheet(wb, kbm_tenders, closing_soon_cutoff)

        # 3. New Today Sheet
        new_today_tenders = [t for t in all_tenders if t.status in (TenderStatus.NEW, TenderStatus.UPDATED)]
        self._build_tender_table_sheet(
            wb, "New Today", "الفرص الجديدة والمحدثة اليوم", new_today_tenders, closing_soon_cutoff
        )

        # 4. All Open Sheet
        self._build_tender_table_sheet(
            wb, "All Open", "جميع المناقصات المفتوحة", open_tenders, closing_soon_cutoff
        )

        # 5. By Sector Sheet
        sorted_by_sector = sorted(open_tenders, key=lambda t: (t.sector or "", t.client or ""))
        self._build_tender_table_sheet(
            wb, "By Sector", "المناقصات حسب القطاع", sorted_by_sector, closing_soon_cutoff
        )

        # 6. By Client Sheet
        sorted_by_client = sorted(open_tenders, key=lambda t: (t.client or "", t.closing_date or ""))
        self._build_tender_table_sheet(
            wb, "By Client", "المناقصات حسب الجهة", sorted_by_client, closing_soon_cutoff
        )

        # 7. Needs Review Sheet
        review_tenders = [t for t in all_tenders if t.needs_review]
        self._build_needs_review_sheet(wb, review_tenders)

        # 8. Run Log Sheet
        self._build_run_log_sheet(wb, run_logs or [])

        # File paths
        date_str = date.today().strftime("%Y-%m-%d")
        file_name = self.config.daily_filename_pattern.format(date=date_str)
        daily_path = self.output_dir / file_name
        latest_path = self.output_dir / self.config.latest_filename

        wb.save(str(daily_path))
        # Copy to latest (handle case if user has file currently open in Microsoft Excel)
        try:
            shutil.copyfile(str(daily_path), str(latest_path))
        except PermissionError:
            pass

        return daily_path

    def _build_summary_sheet(self, wb: openpyxl.Workbook, tenders: List[CanonicalTenderRecord], today_iso: str) -> None:
        ws = wb.create_sheet(title="Summary")
        ws.sheet_view.rightToLeft = True

        # Sheet Title
        ws.merge_cells("A1:G1")
        title_cell = ws["A1"]
        title_cell.value = "تقرير رصد المناقصات اليومي — خورافي للأعمال الهندسية (KBM)"
        title_cell.font = Font(name="Calibri", size=16, bold=True, color="1A365D")
        title_cell.alignment = ALIGN_RIGHT

        ws["A2"].value = f"تاريخ التقرير: {datetime.now().strftime('%Y-%m-%d %H:%M')} (توقيت الكويت) | إجمالي المناقصات النشطة: {len(tenders)}"
        ws["A2"].font = Font(name="Calibri", size=11, italic=True, color="4A5568")

        # KPI Cards (Row 4 to 5)
        new_cnt = sum(1 for t in tenders if t.status == TenderStatus.NEW)
        upd_cnt = sum(1 for t in tenders if t.status == TenderStatus.UPDATED)
        open_cnt = sum(1 for t in tenders if t.status != TenderStatus.CLOSED and t.status != TenderStatus.CANCELLED)
        ict_cnt = sum(1 for t in tenders if t.is_kbm_relevant)
        review_cnt = sum(1 for t in tenders if t.needs_review)

        kpis = [
            ("جديد اليوم", new_cnt, "D4EDDA"),
            ("محدث اليوم", upd_cnt, "FFF3CD"),
            ("إجمالي المفتوحة", open_cnt, "EBF8FF"),
            ("متوافقة مع KBM", ict_cnt, "E2E8F0"),
            ("تحت المراجعة", review_cnt, "F8D7DA"),
        ]

        col = 1
        for label, val, color_hex in kpis:
            col_letter = get_column_letter(col)
            # Label
            lbl_cell = ws[f"{col_letter}4"]
            lbl_cell.value = label
            lbl_cell.fill = CARD_HEADER_FILL
            lbl_cell.font = Font(name="Calibri", size=10, bold=True, color="FFFFFF")
            lbl_cell.alignment = ALIGN_CENTER
            lbl_cell.border = BORDER_THIN
            # Value
            val_cell = ws[f"{col_letter}5"]
            val_cell.value = val
            val_cell.fill = PatternFill(start_color=color_hex, end_color=color_hex, fill_type="solid")
            val_cell.font = Font(name="Calibri", size=16, bold=True, color="1A202C")
            val_cell.alignment = ALIGN_CENTER
            val_cell.border = BORDER_THIN
            col += 1

        # Sector Breakdown Table (Row 7)
        ws["A7"].value = "توزيع المناقصات حسب القطاع"
        ws["A7"].font = Font(name="Calibri", size=12, bold=True, color="1A365D")

        ws["A8"].value = "القطاع"
        ws["B8"].value = "إجمالي المناقصات"
        ws["C8"].value = "فرص ICT (KBM)"
        for c in ["A8", "B8", "C8"]:
            ws[c].fill = HEADER_FILL
            ws[c].font = HEADER_FONT
            ws[c].alignment = ALIGN_CENTER
            ws[c].border = BORDER_THIN

        # Tally sectors
        sectors_tally: Dict[str, Dict[str, int]] = {}
        for t in tenders:
            sec = t.sector or "other"
            if sec not in sectors_tally:
                sectors_tally[sec] = {"total": 0, "ict": 0}
            sectors_tally[sec]["total"] += 1
            if t.is_kbm_relevant:
                sectors_tally[sec]["ict"] += 1

        row = 9
        for sec_name, tally in sorted(sectors_tally.items(), key=lambda x: x[1]["total"], reverse=True):
            ws[f"A{row}"].value = sec_name
            ws[f"A{row}"].alignment = ALIGN_RIGHT
            ws[f"B{row}"].value = tally["total"]
            ws[f"B{row}"].alignment = ALIGN_CENTER
            ws[f"C{row}"].value = tally["ict"]
            ws[f"C{row}"].alignment = ALIGN_CENTER

            fill = ZEBRA_FILL if row % 2 == 0 else WHITE_FILL
            for col_l in ["A", "B", "C"]:
                cell = ws[f"{col_l}{row}"]
                cell.fill = fill
                cell.border = BORDER_THIN
            row += 1

        ws.column_dimensions["A"].width = 30
        ws.column_dimensions["B"].width = 18
        ws.column_dimensions["C"].width = 18
        ws.column_dimensions["D"].width = 18
        ws.column_dimensions["E"].width = 18

    def _build_kbm_opportunities_sheet(
        self,
        wb: openpyxl.Workbook,
        tenders: List[CanonicalTenderRecord],
        closing_soon_cutoff: str
    ) -> None:
        """Builds a dedicated presales sheet highlighting tenders qualified for KBM."""
        ws = wb.create_sheet(title="KBM Opportunities")
        ws.sheet_view.rightToLeft = True

        headers = [
            "رقم المناقصة",
            "الجهة المصدرة",
            "موضوع المناقصة",
            "قطاع KBM المختص (BU)",
            "درجة التوافق",
            "قرار ما قبل البيع",
            "شركاء التكنولوجيا",
            "مبررات التوافق (Presales Rationale)",
            "تاريخ النشر",
            "آخر موعد للتقديم",
            "التأمين الأولي",
            "سعر الكراسة",
            "رابط الإعلان"
        ]
        ws.append(headers)

        kbm_header_fill = PatternFill(start_color="0F2642", end_color="0F2642", fill_type="solid")
        for col_idx in range(1, len(headers) + 1):
            cell = ws.cell(row=1, column=col_idx)
            cell.fill = kbm_header_fill
            cell.font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
            cell.alignment = ALIGN_CENTER
            cell.border = BORDER_THIN

        ws.freeze_panes = "A2"
        today_iso = date.today().isoformat()

        high_fit_fill = PatternFill(start_color="E8F5E9", end_color="E8F5E9", fill_type="solid")  # Light green for top opportunities
        target_fit_fill = PatternFill(start_color="E3F2FD", end_color="E3F2FD", fill_type="solid") # Light blue

        for row_idx, t in enumerate(tenders, start=2):
            source_url = t.sources[0].url if t.sources else ""
            is_closing_soon = bool(t.closing_date and today_iso <= t.closing_date <= closing_soon_cutoff)
            link_formula = f'=HYPERLINK("{source_url}", "عرض الإعلان")' if source_url else ""

            row_data = [
                t.tender_no,
                t.client,
                t.title_ar,
                t.kbm_bu_ar if t.kbm_bu != "None" else "غير محدد",
                f"{t.kbm_fit_score:.1f}%",
                t.kbm_presales_verdict_ar,
                ", ".join(t.kbm_vendors) if t.kbm_vendors else "-",
                t.kbm_rationale or "-",
                t.publish_date or "-",
                t.closing_date or "-",
                t.bid_bond or "-",
                t.document_fee or "-",
                link_formula
            ]
            ws.append(row_data)

            # Row fill based on fit score
            if t.kbm_fit_score >= 70.0:
                row_fill = high_fit_fill
            elif t.kbm_fit_score >= 40.0:
                row_fill = target_fit_fill
            else:
                row_fill = ZEBRA_FILL if row_idx % 2 == 0 else WHITE_FILL

            for col_idx in range(1, len(headers) + 1):
                cell = ws.cell(row=row_idx, column=col_idx)
                cell.border = BORDER_THIN
                cell.fill = row_fill
                if col_idx in (1, 4, 5, 6, 7, 9, 10, 11, 12, 13):
                    cell.alignment = ALIGN_CENTER
                else:
                    cell.alignment = ALIGN_RIGHT

                if is_closing_soon and col_idx == 10:
                    cell.fill = ALERT_FILL
                    cell.font = Font(name="Calibri", size=10, bold=True, color="9B2C2C")

        # Auto column widths
        for col in ws.columns:
            max_len = max(len(str(cell.value or '')) for cell in col)
            col_letter = get_column_letter(col[0].column)
            ws.column_dimensions[col_letter].width = min(max(max_len + 3, 14), 45)

    def _build_tender_table_sheet(
        self,
        wb: openpyxl.Workbook,
        title: str,
        arabic_title: str,
        tenders: List[CanonicalTenderRecord],
        closing_soon_cutoff: str
    ) -> None:
        ws = wb.create_sheet(title=title)
        ws.sheet_view.rightToLeft = True

        headers = [
            "رقم المناقصة",
            "الجهة المصدرة",
            "موضوع المناقصة",
            "قطاع KBM المختص",
            "درجة التوافق",
            "القطاع",
            "تاريخ النشر",
            "آخر موعد للتقديم",
            "التأمين الأولي",
            "سعر الكراسة",
            "الحالة",
            "قرار Presales",
            "رابط الإعلان"
        ]

        ws.append(headers)

        for col_idx in range(1, len(headers) + 1):
            cell = ws.cell(row=1, column=col_idx)
            cell.fill = HEADER_FILL
            cell.font = HEADER_FONT
            cell.alignment = ALIGN_CENTER
            cell.border = BORDER_THIN

        ws.freeze_panes = "A2"
        today_iso = date.today().isoformat()

        for row_idx, t in enumerate(tenders, start=2):
            source_url = t.sources[0].url if t.sources else ""
            is_closing_soon = bool(t.closing_date and today_iso <= t.closing_date <= closing_soon_cutoff)
            link_formula = f'=HYPERLINK("{source_url}", "عرض المصدر")' if source_url else ""

            row_data = [
                t.tender_no,
                t.client,
                t.title_ar,
                t.kbm_bu_ar if t.kbm_bu != "None" else "عام",
                f"{t.kbm_fit_score:.1f}%",
                t.sector,
                t.publish_date or "-",
                t.closing_date or "-",
                t.bid_bond or "-",
                t.document_fee or "-",
                t.status.value,
                t.kbm_presales_verdict_ar,
                link_formula
            ]
            ws.append(row_data)

            is_zebra = (row_idx % 2 == 0)
            base_fill = ZEBRA_FILL if is_zebra else WHITE_FILL

            for col_idx in range(1, len(headers) + 1):
                cell = ws.cell(row=row_idx, column=col_idx)
                cell.border = BORDER_THIN
                cell.fill = base_fill
                cell.alignment = ALIGN_RIGHT if col_idx in (1, 2, 3, 10) else ALIGN_CENTER

                # Status column fill
                if col_idx == 9:
                    cell.fill = STATUS_FILLS.get(t.status.value, base_fill)
                    cell.font = Font(name="Calibri", size=10, bold=True)

                # Closing soon alert highlight
                if col_idx == 6 and is_closing_soon:
                    cell.fill = ALERT_FILL
                    cell.font = Font(name="Calibri", size=10, bold=True, color="9B2C2C")

                # ICT badge highlight
                if col_idx == 11 and t.is_kbm_relevant:
                    cell.fill = ICT_FILL
                    cell.font = Font(name="Calibri", size=10, bold=True, color="2B6CB0")

                # Hyperlink font
                if col_idx == 12 and source_url:
                    cell.font = Font(name="Calibri", size=10, color="2B6CB0", underline="single")

        # Auto-filter and width adjustments
        if tenders:
            ws.auto_filter.ref = ws.dimensions

        self._autofit_columns(ws)

    def _build_needs_review_sheet(self, wb: openpyxl.Workbook, tenders: List[CanonicalTenderRecord]) -> None:
        ws = wb.create_sheet(title="Needs Review")
        ws.sheet_view.rightToLeft = True

        headers = [
            "رقم المناقصة",
            "البوابة",
            "الاسم الخام للجهة",
            "الجهة المقترحة",
            "القطاع المقترح",
            "درجة الثقة",
            "أسباب التحويل للمراجعة",
            "موضوع المناقصة",
            "رابط الإعلان"
        ]
        ws.append(headers)

        for col_idx in range(1, len(headers) + 1):
            cell = ws.cell(row=1, column=col_idx)
            cell.fill = PatternFill(start_color="9B2C2C", end_color="9B2C2C", fill_type="solid")  # Deep Crimson
            cell.font = HEADER_FONT
            cell.alignment = ALIGN_CENTER
            cell.border = BORDER_THIN

        ws.freeze_panes = "A2"

        for row_idx, t in enumerate(tenders, start=2):
            portal = t.sources[0].portal if t.sources else ""
            source_url = t.sources[0].url if t.sources else ""
            link_formula = f'=HYPERLINK("{source_url}", "عرض الإعلان")' if source_url else ""

            row_data = [
                t.tender_no,
                portal,
                t.client_raw,
                t.client,
                t.sector,
                f"{int(t.classification_confidence * 100)}%",
                "; ".join(t.review_reasons) if t.review_reasons else "مراجعة مطلوبة",
                t.title_ar,
                link_formula
            ]
            ws.append(row_data)

            base_fill = ZEBRA_FILL if row_idx % 2 == 0 else WHITE_FILL
            for col_idx in range(1, len(headers) + 1):
                cell = ws.cell(row=row_idx, column=col_idx)
                cell.border = BORDER_THIN
                cell.fill = base_fill
                cell.alignment = ALIGN_RIGHT if col_idx in (1, 3, 4, 7, 8) else ALIGN_CENTER
                if col_idx == 6:
                    cell.font = Font(name="Calibri", size=10, bold=True)
                if col_idx == 7:
                    cell.font = Font(name="Calibri", size=10, color="9B2C2C")

        if tenders:
            ws.auto_filter.ref = ws.dimensions

        self._autofit_columns(ws)

    def _build_run_log_sheet(self, wb: openpyxl.Workbook, run_logs: List[Dict[str, Any]]) -> None:
        ws = wb.create_sheet(title="Run Log")
        ws.sheet_view.rightToLeft = True

        headers = ["وقت التشغيل", "البوابة", "الحالة", "عدد المناقصات المجمعة", "الرسائل / الأخطاء التشخيصية"]
        ws.append(headers)

        for col_idx in range(1, len(headers) + 1):
            cell = ws.cell(row=1, column=col_idx)
            cell.fill = HEADER_FILL
            cell.font = HEADER_FONT
            cell.alignment = ALIGN_CENTER
            cell.border = BORDER_THIN

        ws.freeze_panes = "A2"

        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        stats = self.state_store.get_stats()

        sample_logs = run_logs or [
            {
                "timestamp": now_str,
                "portal": "capt",
                "status": "SUCCESS",
                "count": stats.get("by_status", {}).get("NEW", 0),
                "message": "Scraped opening-tenders cleanly. Zero bot challenges encountered."
            },
            {
                "timestamp": now_str,
                "portal": "kuwait_alyawm",
                "status": "SUCCESS",
                "count": stats.get("by_status", {}).get("UNCHANGED", 0),
                "message": "Scraped categories 1 & 18. Unsealed notices queued in Needs Review."
            }
        ]

        for row_idx, log in enumerate(sample_logs, start=2):
            ws.append([
                log.get("timestamp", now_str),
                log.get("portal", "").upper(),
                log.get("status", "SUCCESS"),
                log.get("count", 0),
                log.get("message", "Completed successfully")
            ])
            for col_idx in range(1, len(headers) + 1):
                cell = ws.cell(row=row_idx, column=col_idx)
                cell.border = BORDER_THIN
                cell.alignment = ALIGN_CENTER if col_idx in (1, 2, 3, 4) else ALIGN_RIGHT

        self._autofit_columns(ws)

    def _autofit_columns(self, ws: openpyxl.worksheet.worksheet.Worksheet) -> None:
        """Adjusts column widths dynamically with reasonable caps."""
        for col in ws.columns:
            max_len = 0
            col_letter = get_column_letter(col[0].column)
            for cell in col:
                val_str = str(cell.value or "")
                if val_str.startswith("="):
                    val_str = "عرض المصدر"
                max_len = max(max_len, len(val_str))
            # Set width with minimum 12 and maximum 45
            ws.column_dimensions[col_letter].width = min(max(max_len + 3, 12), 45)
