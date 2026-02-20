"""Excel export service for valuation outputs."""
from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional

from openpyxl import Workbook

from app.models.scenario import Scenario
from app.services.model.comps import CompsResult

if TYPE_CHECKING:
    pass


class ModelExporter:
    """Export valuation results to Excel."""

    def export_to_excel(
        self,
        file_path: str,
        comps: CompsResult,
        scenarios: list[Scenario],
        weighted_target_price: Optional[float],
        model_output: Optional[Any] = None,
        dcf_result: Optional[Any] = None,
    ) -> str:
        """Write comps and scenarios to an Excel workbook.

        Args:
            file_path: Destination file path for the Excel workbook.
            comps: Comparable company analysis result.
            scenarios: Scenario list to export.
            weighted_target_price: Weighted scenario target price.
            model_output: Optional model output (unused in initial export).
            dcf_result: Optional DCF result (unused in initial export).

        Returns:
            Path to the written Excel file.
        """
        workbook = Workbook()

        comps_sheet = workbook.active
        comps_sheet.title = "Comps"
        comps_sheet.append(
            [
                "Ticker",
                "Company Name",
                "Market Cap",
                "PE",
                "EV/EBITDA",
                "PB",
                "PS",
                "EPS",
                "EBITDA",
                "EPS Source",
                "EBITDA Source",
                "Is Target",
            ]
        )
        for metric in comps.metrics:
            comps_sheet.append(
                [
                    metric.ticker,
                    metric.company_name,
                    metric.market_cap,
                    metric.pe_ratio,
                    metric.ev_to_ebitda,
                    metric.price_to_book,
                    metric.price_to_sales,
                    metric.eps,
                    metric.ebitda,
                    metric.eps_source,
                    metric.ebitda_source,
                    metric.is_target,
                ]
            )

        scenarios_sheet = workbook.create_sheet("Scenarios")
        scenarios_sheet.append(
            [
                "Name",
                "Case Type",
                "Probability",
                "Revenue Growth Rate",
                "Operating Margin",
                "WACC",
                "Terminal Growth Rate",
                "DCF per Share",
                "Comps Implied PE",
                "Comps Implied EV/EBITDA",
            ]
        )
        for scenario in scenarios:
            scenarios_sheet.append(
                [
                    scenario.name,
                    scenario.case_type,
                    scenario.probability,
                    scenario.revenue_growth_rate,
                    scenario.operating_margin,
                    scenario.wacc,
                    scenario.terminal_growth_rate,
                    scenario.dcf_per_share,
                    scenario.comps_implied_pe,
                    scenario.comps_implied_ev_ebitda,
                ]
            )

        scenarios_sheet.append(
            [
                "Weighted Target Price",
                None,
                None,
                None,
                None,
                None,
                None,
                weighted_target_price,
                None,
                None,
            ]
        )

        workbook.save(file_path)
        return file_path
