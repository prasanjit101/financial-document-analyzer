## Importing libraries and files
import os
from config import settings  # ensures env is loaded centrally

try:
    from crewai_tools.tools.serper_dev_tool import SerperDevTool
except Exception:
    SerperDevTool = None
import pdfplumber
import re
from typing import Dict, Tuple, Optional

## Creating search tool
if SerperDevTool is not None:
    search_tool = SerperDevTool()
else:
    # Fallback stub to avoid import errors when crewai_tools isn't installed
    class _NoopSearchTool:
        def __call__(self, *args, **kwargs):
            return ""
    search_tool = _NoopSearchTool()

## Creating custom pdf reader tool
class FinancialDocumentTool():
    @staticmethod
    def read_data_tool(path='data/sample.pdf'):
        """Tool to read data from a pdf file from a path

        Args:
            path (str, optional): Path of the pdf file. Defaults to 'data/sample.pdf'.

        Returns:
            str: Full Financial Document file
        """
        if not os.path.exists(path) or not os.path.isfile(path):
            return ""

        full_report = ""
        try:
            with pdfplumber.open(path) as pdf:
                for page in pdf.pages:
                    content = page.extract_text() or ""
                    if content:
                        # Normalize excessive newlines
                        while "\n\n" in content:
                            content = content.replace("\n\n", "\n")
                        full_report += content + "\n"
        except Exception:
            return ""

        return full_report

## Creating Investment Analysis Tool
class InvestmentTool:
    @staticmethod
    def _normalize_number(raw_number: str) -> Optional[float]:
        """Convert strings like "$1.2B", "3,450", "(120)", "45%", "10m" to float.

        Returns None if the value cannot be parsed.
        """
        if raw_number is None:
            return None

        text = raw_number.strip()

        # Detect negative via parentheses
        is_negative = text.startswith("(") and text.endswith(")")
        text = text.strip("()")

        # Remove currency symbols and spaces
        text = text.replace("$", "").replace("€", "").replace("£", "").replace("₹", "")
        text = text.replace(",", "").strip()

        multiplier = 1.0
        # Handle explicit words
        lower = text.lower()
        if lower.endswith("billion"):
            multiplier = 1e9
            text = text[: -len("billion")]
        elif lower.endswith("million"):
            multiplier = 1e6
            text = text[: -len("million")]
        elif lower.endswith("thousand"):
            multiplier = 1e3
            text = text[: -len("thousand")]

        # Handle suffix letters
        lower = text.lower()
        if lower.endswith("b"):
            multiplier = 1e9
            text = text[:-1]
        elif lower.endswith("m"):
            multiplier = 1e6
            text = text[:-1]
        elif lower.endswith("k"):
            multiplier = 1e3
            text = text[:-1]

        # Remove percent sign (we return raw number; caller decides interpretation)
        is_percent = text.endswith("%")
        if is_percent:
            text = text[:-1]

        try:
            value = float(text)
            value = -value if is_negative else value
            value = value * multiplier
            return value
        except Exception:
            return None

    @staticmethod
    def _extract_numbers_from_line(line: str) -> Optional[str]:
        """Extract the last number-like token from a line.

        Supports forms like 1,234, 1.2B, (123), 45%, 10m, $2.3B
        """
        pattern = r"(?:\$|€|£|₹)?\(?[0-9]{1,3}(?:,[0-9]{3})*(?:\.[0-9]+)?\)?%?|(?:\$|€|£|₹)?\(?[0-9]+(?:\.[0-9]+)?\)?%?[bmkBMK]?|[0-9]+%"
        matches = re.findall(pattern, line)
        if not matches:
            return None
        return matches[-1]

    @staticmethod
    def _parse_financial_text(financial_document_data: str) -> Dict[str, float]:
        """Parse common financial metrics from text.

        Returns a dictionary with keys like revenue, net_income, operating_income, ebitda,
        eps, debt, cash, fcf, gross_margin, operating_margin, net_margin, current_ratio,
        quick_ratio, roe, roa, yoy_revenue_growth.
        """
        metrics: Dict[str, float] = {}

        if not financial_document_data:
            return metrics

        lines = [l.strip() for l in financial_document_data.split("\n") if l.strip()]

        metric_map: Dict[str, re.Pattern] = {
            "revenue": re.compile(r"\b(total\s+)?revenue\b", re.I),
            "net_income": re.compile(r"\b(net\s+income|net\s+earnings|profit)\b", re.I),
            "operating_income": re.compile(r"\b(operating\s+income|operating\s+profit|EBIT)\b", re.I),
            "ebitda": re.compile(r"\bEBITDA\b", re.I),
            "eps": re.compile(r"\b(EPS|earnings\s+per\s+share)\b", re.I),
            "debt": re.compile(r"\b(total\s+debt|long-?term\s+debt)\b", re.I),
            "cash": re.compile(r"\b(cash(\s+and\s+cash\s+equivalents)?)\b", re.I),
            "fcf": re.compile(r"\b(free\s+cash\s+flow|FCF)\b", re.I),
            "gross_margin": re.compile(r"\bgross\s+margin\b", re.I),
            "operating_margin": re.compile(r"\boperating\s+margin\b", re.I),
            "net_margin": re.compile(r"\bnet\s+margin\b", re.I),
            "current_ratio": re.compile(r"\bcurrent\s+ratio\b", re.I),
            "quick_ratio": re.compile(r"\bquick\s+ratio\b", re.I),
            "roe": re.compile(r"\b(ROE|return\s+on\s+equity)\b", re.I),
            "roa": re.compile(r"\b(ROA|return\s+on\s+assets)\b", re.I),
            "yoy": re.compile(r"\b(YoY|year[-\s]*over[-\s]*year)\b", re.I),
            "growth": re.compile(r"\b(growth|increase|decrease)\b", re.I),
        }

        for line in lines:
            for key, pattern in metric_map.items():
                if pattern.search(line):
                    raw = InvestmentTool._extract_numbers_from_line(line)
                    num = InvestmentTool._normalize_number(raw) if raw else None
                    if num is not None:
                        # Map derived keys
                        target_key = key
                        if key == "yoy" or key == "growth":
                            target_key = "yoy_revenue_growth" if "revenue" in line.lower() else "growth_indicator"
                        if target_key not in metrics:
                            metrics[target_key] = num

        # Derive margins if not present
        revenue = metrics.get("revenue")
        net_income = metrics.get("net_income")
        operating_income = metrics.get("operating_income")
        if revenue is not None and revenue != 0:
            if "net_margin" not in metrics and net_income is not None:
                metrics["net_margin"] = (net_income / revenue) * 100.0
            if "operating_margin" not in metrics and operating_income is not None:
                metrics["operating_margin"] = (operating_income / revenue) * 100.0

        return metrics

    @staticmethod
    def analyze_investment_tool(financial_document_data):
        """Provide a concise investment analysis from extracted financial text.

        Steps:
        - Parse key metrics from text
        - Compute simple heuristics
        - Output a brief recommendation
        """
        if not financial_document_data:
            return "No financial document text provided."

        metrics = InvestmentTool._parse_financial_text(financial_document_data)

        # Simple scoring model
        score = 0
        notes = []

        revenue = metrics.get("revenue")
        net_margin = metrics.get("net_margin")
        operating_margin = metrics.get("operating_margin")
        ebitda = metrics.get("ebitda")
        debt = metrics.get("debt")
        cash = metrics.get("cash")
        fcf = metrics.get("fcf")
        roe = metrics.get("roe")
        yoy_growth = metrics.get("yoy_revenue_growth")

        if roe is not None:
            if roe >= 15:
                score += 2
                notes.append("Strong ROE")
            elif roe >= 8:
                score += 1
                notes.append("Healthy ROE")
            else:
                score -= 1
                notes.append("Weak ROE")

        if net_margin is not None:
            if net_margin >= 15:
                score += 2
                notes.append("High net margin")
            elif net_margin >= 8:
                score += 1
                notes.append("Moderate net margin")
            else:
                score -= 1
                notes.append("Thin net margin")

        if yoy_growth is not None:
            if yoy_growth >= 10:
                score += 2
                notes.append("Double-digit YoY growth")
            elif yoy_growth >= 3:
                score += 1
                notes.append("Positive YoY growth")
            elif yoy_growth < 0:
                score -= 1
                notes.append("Negative YoY growth")

        if revenue is not None and revenue != 0 and debt is not None:
            leverage = (debt / revenue)
            if leverage > 1.0:
                score -= 2
                notes.append("High leverage vs revenue")
            elif leverage > 0.5:
                score -= 1
                notes.append("Elevated leverage")

        if cash is not None and debt is not None:
            if cash >= debt:
                score += 1
                notes.append("Cash covers debt")
            else:
                notes.append("Cash below debt")

        if fcf is not None:
            if fcf > 0:
                score += 1
                notes.append("Positive FCF")
            else:
                score -= 1
                notes.append("Negative FCF")

        if ebitda is not None and ebitda <= 0:
            score -= 2
            notes.append("EBITDA at or below zero")

        # Recommendation
        if score >= 3:
            recommendation = "Buy"
        elif score >= 1:
            recommendation = "Accumulate / Hold"
        elif score >= -1:
            recommendation = "Neutral / Watch"
        else:
            recommendation = "Sell / Reduce"

        # Prepare output
        lines = []
        lines.append("Investment Analysis")
        lines.append("- Recommendation: " + recommendation)
        lines.append(f"- Score: {score}")
        if notes:
            lines.append("- Signals: " + ", ".join(notes))

        def fmt(name: str, key: str, suffix: str = ""):
            val = metrics.get(key)
            if val is None:
                return None
            if key.endswith("margin") or key in ("roe", "roa", "yoy_revenue_growth"):
                return f"- {name}: {val:.2f}%"
            # Show in compact units
            if abs(val) >= 1e9:
                return f"- {name}: {val/1e9:.2f}B{suffix}"
            if abs(val) >= 1e6:
                return f"- {name}: {val/1e6:.2f}M{suffix}"
            if abs(val) >= 1e3:
                return f"- {name}: {val/1e3:.2f}K{suffix}"
            return f"- {name}: {val:.2f}{suffix}"

        detail_keys: Tuple[Tuple[str, str, str], ...] = (
            ("Revenue", "revenue", ""),
            ("Net Income", "net_income", ""),
            ("Operating Income", "operating_income", ""),
            ("EBITDA", "ebitda", ""),
            ("EPS", "eps", ""),
            ("Debt", "debt", ""),
            ("Cash", "cash", ""),
            ("Free Cash Flow", "fcf", ""),
            ("Gross Margin", "gross_margin", ""),
            ("Operating Margin", "operating_margin", ""),
            ("Net Margin", "net_margin", ""),
            ("Current Ratio", "current_ratio", ""),
            ("Quick Ratio", "quick_ratio", ""),
            ("ROE", "roe", ""),
            ("ROA", "roa", ""),
            ("YoY Revenue Growth", "yoy_revenue_growth", ""),
        )

        lines.append("\nKey Metrics")
        for name, key, suffix in detail_keys:
            s = fmt(name, key, suffix)
            if s:
                lines.append(s)

        return "\n".join(lines)

## Creating Risk Assessment Tool
class RiskTool:
    @staticmethod
    def create_risk_assessment_tool(financial_document_data):        
        """Generate a concise risk assessment from extracted financial text.

        Evaluates leverage, liquidity, profitability and growth to score risk.
        Returns a short, structured summary and risk score 1 (low) to 5 (high).
        """
        if not financial_document_data:
            return "No financial document text provided."

        metrics = InvestmentTool._parse_financial_text(financial_document_data)

        risk_points = 0
        factors = []

        revenue = metrics.get("revenue")
        debt = metrics.get("debt")
        cash = metrics.get("cash")
        current_ratio = metrics.get("current_ratio")
        quick_ratio = metrics.get("quick_ratio")
        net_margin = metrics.get("net_margin")
        operating_margin = metrics.get("operating_margin")
        yoy_growth = metrics.get("yoy_revenue_growth")
        fcf = metrics.get("fcf")

        # Leverage
        if revenue is not None and revenue != 0 and debt is not None:
            leverage = debt / revenue
            if leverage > 1.5:
                risk_points += 2
                factors.append("Very high leverage vs revenue")
            elif leverage > 0.8:
                risk_points += 1
                factors.append("Elevated leverage")

        # Liquidity
        if current_ratio is not None:
            if current_ratio < 1.0:
                risk_points += 2
                factors.append("Current ratio < 1.0")
            elif current_ratio < 1.5:
                risk_points += 1
                factors.append("Current ratio below 1.5")
        if quick_ratio is not None and quick_ratio < 1.0:
            risk_points += 1
            factors.append("Quick ratio < 1.0")

        # Cash vs Debt
        if cash is not None and debt is not None and cash < debt * 0.5:
            risk_points += 1
            factors.append("Cash covers <50% of debt")

        # Profitability
        if net_margin is not None and net_margin < 5:
            risk_points += 1
            factors.append("Thin net margin")
        if operating_margin is not None and operating_margin < 7:
            risk_points += 1
            factors.append("Low operating margin")

        # Growth and cash generation
        if yoy_growth is not None and yoy_growth < 0:
            risk_points += 1
            factors.append("Negative YoY revenue growth")
        if fcf is not None and fcf < 0:
            risk_points += 1
            factors.append("Negative free cash flow")

        # Map points to 1-5 score
        if risk_points <= 1:
            score = 1
            label = "Low"
        elif risk_points == 2:
            score = 2
            label = "Moderate-Low"
        elif risk_points == 3:
            score = 3
            label = "Moderate"
        elif risk_points == 4:
            score = 4
            label = "Elevated"
        else:
            score = 5
            label = "High"

        summary = [
            "Risk Assessment",
            f"- Risk Score: {score} ({label})",
        ]
        if factors:
            summary.append("- Factors: " + ", ".join(factors))

        return "\n".join(summary)