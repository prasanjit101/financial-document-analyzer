## Importing libraries and files
import os
import asyncio
import json
from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional, Tuple, Set

from config import settings  # ensures env is loaded centrally
from crewai.tools import BaseTool
try:
    from crewai_tools.tools.serper_dev_tool import SerperDevTool  # type: ignore
except Exception:
    SerperDevTool = None
import pdfplumber
import re

## Creating search tool
if SerperDevTool is not None:
    # SerperDevTool already implements the required interface for CrewAI
    search_tool = SerperDevTool()
else:
    class _NoopSearchTool(BaseTool):  # type: ignore
        name: str = "Search (noop)"
        description: str = (
            "No-op search tool used when Serper API is not configured. Returns empty string."
        )

        def _run(self, query: str) -> str:  # type: ignore[override]
            return ""
    search_tool = _NoopSearchTool()

## Creating custom pdf reader tool and analysis helpers


@dataclass
class DocumentExtractionResult:
    status: str
    file_path: str
    page_count: int
    classification: str
    indicators: List[str]
    full_text: str
    truncated: bool
    note: str = ""


@dataclass
class DetectedMetric:
    name: str
    value: str
    unit: str
    evidence: str


_CLASSIFICATION_PATTERNS: List[Tuple[str, str]] = [
    (r"balance\s+sheet|total\s+assets|shareholders'?\s+equity", "balance_sheet"),
    (r"income\s+statement|revenue|gross\s+profit", "income_statement"),
    (r"cash\s+flow|operating\s+activities|free\s+cash\s+flow", "cash_flow_statement"),
    (r"management'?s\s+discussion|md&a", "management_discussion"),
    (r"quarterly\s+report|10-q", "quarterly_report"),
    (r"annual\s+report|10-k", "annual_report"),
]

_FINANCIAL_KEYWORDS: List[str] = [
    "revenue",
    "net income",
    "ebitda",
    "operating income",
    "cash flow",
    "assets",
    "liabilities",
    "equity",
    "margin",
    "earnings",
]

_METRIC_PATTERNS: Dict[str, re.Pattern[str]] = {
    "revenue": re.compile(r"revenue(?:\s+(?:of|was|totaled))?\s*[$€£]?([\d,.]+)\s*(million|billion|thousand|m|bn|k)?", re.IGNORECASE),
    "net_income": re.compile(r"net\s+income(?:\s+(?:of|was|totaled))?\s*[$€£]?([\d,.]+)\s*(million|billion|thousand|m|bn|k)?", re.IGNORECASE),
    "ebitda": re.compile(r"ebitda(?:\s+(?:of|was|totaled))?\s*[$€£]?([\d,.]+)\s*(million|billion|thousand|m|bn|k)?", re.IGNORECASE),
    "cash_flow": re.compile(r"cash\s+flow(?:\s+(?:of|from|was|totaled))?\s*[$€£]?([\d,.]+)\s*(million|billion|thousand|m|bn|k)?", re.IGNORECASE),
    "gross_margin": re.compile(r"gross\s+margin\s+(?:of|was)?\s*([\d.]+)\s*%", re.IGNORECASE),
    "operating_margin": re.compile(r"operating\s+margin\s+(?:of|was)?\s*([\d.]+)\s*%", re.IGNORECASE),
}


def _clean_text(value: str) -> str:
    value = value.replace("\u2013", "-").replace("\u2014", "-")
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def _classify_document(text: str) -> Tuple[str, List[str]]:
    lowered = text.lower()
    for pattern, label in _CLASSIFICATION_PATTERNS:
        if re.search(pattern, lowered):
            indicators = [kw for kw in _FINANCIAL_KEYWORDS if kw in lowered]
            return label, indicators
    indicators = [kw for kw in _FINANCIAL_KEYWORDS if kw in lowered]
    classification = "financial" if indicators else "unknown"
    return classification, indicators


def _extract_metrics(text: str, max_metrics: int = 10) -> List[DetectedMetric]:
    metrics: List[DetectedMetric] = []
    lowered = text.lower()
    for name, pattern in _METRIC_PATTERNS.items():
        for match in pattern.finditer(text):
            raw_value = match.group(1) if match.groups() else match.group(0)
            unit = match.group(2) if match.lastindex and match.lastindex >= 2 else "-"
            evidence_start = max(match.start() - 40, 0)
            evidence_end = min(match.end() + 40, len(text))
            evidence = _clean_text(text[evidence_start:evidence_end])
            metrics.append(DetectedMetric(name=name, value=_clean_text(raw_value), unit=_clean_text(unit or "-"), evidence=evidence))
            if len(metrics) >= max_metrics:
                return metrics
    # simple keyword-based revenue growth indicator
    if "year-over-year" in lowered or "yoy" in lowered:
        metrics.append(DetectedMetric(name="growth_rate", value="year-over-year mentioned", unit="-", evidence="YOY growth reference detected"))
    return metrics


def _safe_json_loads(value: str) -> Optional[Any]:
    try:
        return json.loads(value)
    except Exception:
        return None


def _normalize_metrics_list(items: Any) -> List[Dict[str, str]]:
    metrics: List[Dict[str, str]] = []
    if items is None:
        return metrics
    if isinstance(items, str):
        parsed = _safe_json_loads(items)
        if parsed is not None:
            return _normalize_metrics_list(parsed)
        return [{"name": "metric", "value": items, "unit": "-", "evidence": ""}]
    if isinstance(items, dict):
        items = [items]
    if isinstance(items, list):
        for entry in items:
            if isinstance(entry, dict):
                name = str(entry.get("name") or entry.get("metric") or entry.get("label") or entry.get("key") or "metric")
                value = str(entry.get("value") or entry.get("amount") or entry.get("figure") or entry.get("score") or "-")
                unit = str(entry.get("unit") or entry.get("units") or entry.get("currency") or "-")
                evidence = str(entry.get("evidence") or entry.get("note") or entry.get("source") or "")
                metrics.append({"name": name, "value": value, "unit": unit, "evidence": evidence})
            elif entry is not None:
                metrics.append({"name": "metric", "value": str(entry), "unit": "-", "evidence": ""})
    return metrics


def _merge_metric_lists(existing: List[Dict[str, str]], additional: List[Dict[str, str]]) -> List[Dict[str, str]]:
    merged: List[Dict[str, str]] = []
    seen: Set[Tuple[str, str, str, str]] = set()
    for collection in (existing, additional):
        for metric in collection:
            name = metric.get("name", "metric")
            value = metric.get("value", "-")
            unit = metric.get("unit", "-")
            evidence = metric.get("evidence", "")
            key = (str(name), str(value), str(unit), str(evidence))
            if key in seen:
                continue
            seen.add(key)
            merged.append({
                "name": str(name),
                "value": str(value),
                "unit": str(unit),
                "evidence": str(evidence),
            })
    return merged


def _strip_code_fence(value: str) -> str:
    trimmed = value.strip()
    if trimmed.startswith("```"):
        lines = trimmed.splitlines()
        if len(lines) >= 2:
            # drop opening fence (and optional language) and closing fence if present
            lines = lines[1:]
            if lines and lines[-1].strip().startswith("```"):
                lines = lines[:-1]
            trimmed = "\n".join(lines).strip()
    return trimmed


def _discover_document_path(payload: Dict[str, Any]) -> Optional[str]:
    path_keys = [
        "file_path",
        "path",
        "document_path",
        "source_path",
        "document",
        "input_path",
    ]
    for key in path_keys:
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()

    for nested_key in [
        "data_package",
        "dataPackage",
        "structured_financial_data",
        "financial_data",
        "risk_package",
    ]:
        nested = payload.get(nested_key)
        if isinstance(nested, str):
            maybe = _safe_json_loads(nested)
            if isinstance(maybe, dict):
                nested = maybe
        if isinstance(nested, dict):
            found = _discover_document_path(nested)
            if found:
                return found
    return None


def _collect_structured_segments(payload: Dict[str, Any], seen: Optional[Set[int]] = None) -> Tuple[List[str], List[Dict[str, str]]]:
    if seen is None:
        seen = set()
    if not isinstance(payload, dict):
        return [], []
    if id(payload) in seen:
        return [], []
    seen.add(id(payload))

    segments: List[str] = []
    metrics_accum: List[Dict[str, str]] = []

    for key in ["metrics", "detected_metrics", "target_metrics"]:
        if key in payload:
            normalized = _normalize_metrics_list(payload.get(key))
            if normalized:
                metrics_accum.extend(normalized)
                for metric in normalized:
                    unit_part = "" if metric["unit"] in {"", "-"} else f" {metric['unit']}"
                    evidence_part = f" (evidence: {metric['evidence']})" if metric["evidence"] else ""
                    segments.append(f"Metric {metric['name']}: {metric['value']}{unit_part}{evidence_part}")

    ratio_candidates = payload.get("ratios") or payload.get("calculated_ratios")
    if ratio_candidates:
        parsed = ratio_candidates
        if isinstance(parsed, str):
            maybe = _safe_json_loads(parsed)
            if maybe is not None:
                parsed = maybe
        if isinstance(parsed, dict):
            parsed = [parsed]
        if isinstance(parsed, list):
            for ratio in parsed:
                if isinstance(ratio, dict):
                    name = str(ratio.get("name") or ratio.get("metric") or "ratio")
                    value = str(ratio.get("value") or ratio.get("score") or ratio.get("amount") or "-")
                    basis = str(ratio.get("basis") or ratio.get("inputs") or "-")
                    note = str(ratio.get("note") or ratio.get("assumption") or "")
                    note_part = f" (note: {note})" if note else ""
                    segments.append(f"Ratio {name}: {value} (basis: {basis}){note_part}")
                elif ratio is not None:
                    segments.append(f"Ratio: {ratio}")

    def _extend_from_sequence(entries: Any, prefix: str) -> None:
        if not entries:
            return
        parsed_entries = entries
        if isinstance(parsed_entries, str):
            maybe = _safe_json_loads(parsed_entries)
            if maybe is not None:
                parsed_entries = maybe
        if isinstance(parsed_entries, dict):
            parsed_entries = [parsed_entries]
        if not isinstance(parsed_entries, list):
            parsed_entries = [parsed_entries]
        for entry in parsed_entries:
            if entry is None:
                continue
            if isinstance(entry, dict):
                details = ", ".join(f"{k}={v}" for k, v in entry.items() if v not in (None, ""))
                segments.append(f"{prefix} {details}".strip())
            else:
                segments.append(f"{prefix} {entry}".strip())

    for key, prefix in [
        ("insights", "Insight:"),
        ("trends", "Trend:"),
        ("signals", "Signal:"),
        ("assumptions", "Assumption:"),
        ("uncertainties", "Uncertainty:"),
        ("factors", "Factor:"),
        ("mitigants", "Mitigant:"),
        ("stress_tests", "Stress Test:"),
        ("monitoring", "Monitoring:"),
        ("notes", "Note:"),
    ]:
        if key in payload:
            _extend_from_sequence(payload.get(key), prefix)

    for nested_key in [
        "data_package",
        "dataPackage",
        "structured_financial_data",
        "financial_data",
        "risk_package",
    ]:
        if nested_key in payload:
            nested = payload.get(nested_key)
            if isinstance(nested, str):
                maybe = _safe_json_loads(nested)
                if maybe is not None:
                    nested = maybe
            if isinstance(nested, dict):
                child_segments, child_metrics = _collect_structured_segments(nested, seen)
                segments.extend(child_segments)
                metrics_accum.extend(child_metrics)

    return segments, metrics_accum


class FinancialDocumentTool:
    @staticmethod
    def read_data_tool(path: str = "data/sample.pdf") -> DocumentExtractionResult:
        if not path or not os.path.exists(path) or not os.path.isfile(path):
            return DocumentExtractionResult(
                status="error",
                file_path=path,
                page_count=0,
                classification="missing",
                indicators=[],
                full_text="",
                truncated=False,
                note="File not found or inaccessible.",
            )

        max_pages = getattr(settings, "MAX_PDF_PAGES", 200)
        max_chars = getattr(settings, "MAX_EXTRACTED_TEXT_CHARS", 2_000_000)
        aggregated_text: List[str] = []
        extracted_chars = 0
        page_count = 0
        truncated = False

        try:
            with pdfplumber.open(path) as pdf:
                for idx, page in enumerate(pdf.pages):
                    if idx >= max_pages:
                        truncated = True
                        break
                    try:
                        content = page.extract_text() or ""
                    except Exception:
                        content = ""
                    content = content.strip()
                    if content:
                        content = content.replace("\r", "\n")
                        content = re.sub(r"\n{2,}", "\n", content)
                        remaining = max_chars - extracted_chars
                        if remaining <= 0:
                            truncated = True
                            break
                        if len(content) > remaining:
                            content = content[:remaining]
                            truncated = True
                        aggregated_text.append(content)
                        extracted_chars += len(content)
                    page_count += 1
        except Exception as exc:  # pragma: no cover - defensive
            return DocumentExtractionResult(
                status="error",
                file_path=path,
                page_count=page_count,
                classification="error",
                indicators=[],
                full_text="",
                truncated=truncated,
                note=f"Failed to extract PDF text: {exc}",
            )

        full_text = "\n".join(aggregated_text)
        classification, indicators = _classify_document(full_text)
        return DocumentExtractionResult(
            status="ok",
            file_path=path,
            page_count=page_count,
            classification=classification,
            indicators=indicators,
            full_text=full_text,
            truncated=truncated,
            note="" if full_text else "No extractable text detected.",
        )

    @staticmethod
    async def read_data_tool_async(path: str = "data/sample.pdf") -> DocumentExtractionResult:
        return await asyncio.to_thread(FinancialDocumentTool.read_data_tool, path)

    @staticmethod
    def serialize_result(result: DocumentExtractionResult, include_text: bool = True) -> str:
        payload: Dict[str, Any] = asdict(result)
        preview_len = getattr(settings, "PDF_PREVIEW_CHARS", 4000)
        payload["preview"] = result.full_text[:preview_len]
        if not include_text:
            payload.pop("full_text", None)
        payload["detected_metrics"] = [asdict(metric) for metric in _extract_metrics(result.full_text)] if result.full_text else []
        return json.dumps(payload, ensure_ascii=False)


class ReadFinancialDocumentTool(BaseTool):  # type: ignore
    name: str = "Read Financial Document"
    description: str = (
        "Extracts text and metadata from a PDF at the given file path. Returns JSON with classification and metrics."
    )

    def _run(self, path: str = "data/sample.pdf") -> str:  # type: ignore[override]
        result = FinancialDocumentTool.read_data_tool(path=path)
        return FinancialDocumentTool.serialize_result(result)

    async def _arun(self, path: str = "data/sample.pdf") -> str:  # type: ignore[override]
        result = await FinancialDocumentTool.read_data_tool_async(path=path)
        return FinancialDocumentTool.serialize_result(result)


def _normalize_input(financial_document_data: Any) -> Tuple[str, Dict[str, Any]]:
    payload: Dict[str, Any] = {}

    if isinstance(financial_document_data, dict):
        payload = financial_document_data
    elif isinstance(financial_document_data, list):
        payload = {"metrics": financial_document_data}
    elif isinstance(financial_document_data, str):
        cleaned = _strip_code_fence(financial_document_data)
        parsed = _safe_json_loads(cleaned)
        if isinstance(parsed, dict):
            payload = parsed
        elif isinstance(parsed, list):
            payload = {"metrics": parsed}
        else:
            return cleaned, {"full_text": cleaned}
    elif financial_document_data is None:
        payload = {}
    else:
        payload = {"value": financial_document_data}

    # Normalize nested JSON strings that may contain structured data
    for key in [
        "data_package",
        "dataPackage",
        "structured_financial_data",
        "financial_data",
        "risk_package",
    ]:
        if key in payload and isinstance(payload[key], str):
            maybe = _safe_json_loads(_strip_code_fence(str(payload[key])))
            if isinstance(maybe, dict):
                payload[key] = maybe

    # Promote nested classification/indicator hints if missing at top level
    if not payload.get("classification"):
        for key in ["data_package", "dataPackage", "structured_financial_data", "financial_data"]:
            nested = payload.get(key)
            if isinstance(nested, dict) and nested.get("classification"):
                payload["classification"] = nested.get("classification")
                break
    if not payload.get("indicators"):
        for key in ["data_package", "dataPackage", "structured_financial_data", "financial_data"]:
            nested = payload.get(key)
            if isinstance(nested, dict) and nested.get("indicators"):
                payload["indicators"] = nested.get("indicators")
                break

    existing_metrics = _normalize_metrics_list(payload.get("detected_metrics"))
    if existing_metrics:
        payload["detected_metrics"] = existing_metrics

    text = str(payload.get("full_text") or payload.get("preview") or payload.get("text") or "")

    structured_segments, structured_metrics = _collect_structured_segments(payload)
    if structured_metrics:
        payload["detected_metrics"] = _merge_metric_lists(
            _normalize_metrics_list(payload.get("detected_metrics")),
            structured_metrics,
        )

    if not text and structured_segments:
        text = "\n".join(structured_segments)

    doc_path = _discover_document_path(payload)
    if not text and doc_path:
        extraction = FinancialDocumentTool.read_data_tool(doc_path)
        payload.setdefault("status", extraction.status)
        payload.setdefault("classification", extraction.classification)
        payload.setdefault("indicators", extraction.indicators)
        payload.setdefault("page_count", extraction.page_count)
        payload.setdefault("truncated", extraction.truncated)
        payload.setdefault("file_path", extraction.file_path)
        if extraction.note and not payload.get("note"):
            payload["note"] = extraction.note
        if extraction.full_text:
            text = extraction.full_text
            payload.setdefault("full_text", extraction.full_text)
            detected_from_text = [asdict(metric) for metric in _extract_metrics(extraction.full_text)]
            payload["detected_metrics"] = _merge_metric_lists(
                _normalize_metrics_list(payload.get("detected_metrics")),
                detected_from_text,
            )

    if not text and payload.get("note"):
        text = str(payload["note"])

    return text.strip(), payload


class InvestmentTool:
    @staticmethod
    def analyze_investment_tool(financial_document_data: Any) -> str:
        text, payload = _normalize_input(financial_document_data)
        if not text:
            return json.dumps({
                "status": "error",
                "message": "No financial document text provided.",
            })

        lowered = text.lower()
        metrics = payload.get("detected_metrics") or [asdict(metric) for metric in _extract_metrics(text)]

        positives = sum(1 for kw in ["increase", "growth", "record", "improved", "expanded"] if kw in lowered)
        negatives = sum(1 for kw in ["decline", "decrease", "loss", "deteriorated", "restructuring"] if kw in lowered)

        stance = "Hold"
        if positives > negatives + 1:
            stance = "Buy"
        elif negatives > positives + 1:
            stance = "Sell"

        rationale: List[str] = []
        if stance == "Buy":
            rationale.append("Positive growth language outweighs risks.")
        elif stance == "Sell":
            rationale.append("Multiple negative performance signals detected.")
        else:
            rationale.append("Mixed signals suggest maintaining current positioning.")

        if payload.get("classification"):
            rationale.append(f"Document classified as {payload['classification'].replace('_', ' ')}.")

        signals: List[str] = []
        if "cash flow" in lowered:
            signals.append("Cash flow discussed")
        if "margin" in lowered:
            signals.append("Margin commentary present")
        if "guidance" in lowered:
            signals.append("Guidance provided")
        if "debt" in lowered:
            signals.append("Debt profile referenced")
        if not signals:
            signals.append("No explicit financial signals detected")

        assumptions = [
            "Metrics interpreted at face value from supplied text.",
            "No external market data incorporated.",
        ]

        target_metrics = {metric["name"]: metric.get("value", "n/a") for metric in metrics[:4]} if metrics else {}

        result = {
            "status": "ok",
            "stance": stance,
            "rationale": rationale,
            "signals": signals,
            "assumptions": assumptions,
            "target_metrics": target_metrics,
            "detected_metrics": metrics,
        }
        return json.dumps(result, ensure_ascii=False)

    @staticmethod
    async def analyze_investment_tool_async(financial_document_data: Any) -> str:
        return await asyncio.to_thread(InvestmentTool.analyze_investment_tool, financial_document_data)


# BaseTool wrapper exposing investment analysis as a CrewAI tool
class AnalyzeInvestmentTool(BaseTool):  # type: ignore
    name: str = "Analyze Investment"
    description: str = (
        "Generates a concise, structured investment overview from extracted financial text."
    )

    def _run(self, financial_document_data: Any) -> str:  # type: ignore[override]
        return InvestmentTool.analyze_investment_tool(financial_document_data)

    async def _arun(self, financial_document_data: Any) -> str:  # type: ignore[override]
        return await InvestmentTool.analyze_investment_tool_async(financial_document_data)


class RiskTool:
    @staticmethod
    def create_risk_assessment_tool(financial_document_data: Any) -> str:
        text, payload = _normalize_input(financial_document_data)
        if not text:
            return json.dumps({
                "status": "error",
                "message": "No financial document text provided.",
            })

        lowered = text.lower()
        risk_score = 3

        risk_factors: List[str] = []
        mitigants: List[str] = []

        if any(term in lowered for term in ["leverage", "high debt", "debt to equity", "covenant"]):
            risk_score += 1
            risk_factors.append("Elevated leverage indicators present.")
        if any(term in lowered for term in ["liquidity", "cash balance", "working capital"]):
            mitigants.append("Liquidity discussed, suggesting active management.")
        if any(term in lowered for term in ["loss", "decline", "headwinds", "downturn"]):
            risk_score += 1
            risk_factors.append("Negative performance language detected.")
        if any(term in lowered for term in ["record", "improved", "growth", "strong"]):
            risk_score -= 1
            mitigants.append("Positive performance descriptors present.")
        if "guidance" in lowered and "lower" in lowered:
            risk_score += 1
            risk_factors.append("Guidance revisions trending negatively.")

        risk_score = max(1, min(5, risk_score))

        if not risk_factors:
            risk_factors.append("No explicit red flags detected in provided text.")
        if mitigants:
            risk_factors.extend(mitigants)

        confidence = "medium"
        if payload.get("classification") in {"balance_sheet", "income_statement", "cash_flow_statement"}:
            confidence = "high"
        elif len(text) < 1000:
            confidence = "low"

        stress_tests = []
        if "interest rate" in lowered:
            stress_tests.append("Assess sensitivity to interest rate shifts.")
        if "supply chain" in lowered:
            stress_tests.append("Model supply chain disruption scenarios.")
        if not stress_tests:
            stress_tests.append("Run base, downside, and severe revenue contraction scenarios.")

        result = {
            "status": "ok",
            "score": risk_score,
            "factors": risk_factors[:6],
            "stress_tests": stress_tests[:3],
            "confidence": confidence,
        }
        return json.dumps(result, ensure_ascii=False)

    @staticmethod
    async def create_risk_assessment_tool_async(financial_document_data: Any) -> str:
        return await asyncio.to_thread(RiskTool.create_risk_assessment_tool, financial_document_data)


class CreateRiskAssessmentTool(BaseTool):  # type: ignore
    name: str = "Create Risk Assessment"
    description: str = (
        "Generates a concise risk assessment and score from extracted financial text."
    )

    def _run(self, financial_document_data: Any) -> str:  # type: ignore[override]
        return RiskTool.create_risk_assessment_tool(financial_document_data)

    async def _arun(self, financial_document_data: Any) -> str:  # type: ignore[override]
        return await RiskTool.create_risk_assessment_tool_async(financial_document_data)

risk_assessment_tool = CreateRiskAssessmentTool()
analyze_investment_tool = AnalyzeInvestmentTool()
read_financial_document_tool = ReadFinancialDocumentTool()