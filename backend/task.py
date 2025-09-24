## Importing libraries and files
from crewai import Task

from agents import financial_analyst, verifier, investment_advisor, risk_assessor
from tools import (
    search_tool,
    read_financial_document_tool,
    analyze_investment_tool,
    risk_assessment_tool,
)

## Creating a task to help solve user's query
analyze_financial_document = Task(
    description="""
Analyze the document at {file_path} in relation to the user's query {query}.
Follow these steps strictly:
1) Use tools to extract text from the document.
2) Detect concrete financial metrics mentioned (e.g., revenue, EBITDA, margins, cash flow, assets, liabilities, growth rates) and capture their values and units if present.
3) Provide a concise, non-personalized investment overview grounded in the detected evidence.
4) Provide a concise risk assessment grounded in detected evidence and simple, transparent heuristics.

Rules:
- Base all claims on tool outputs or explicit text. Do not guess.
- Cite evidence briefly by quoting short phrases when appropriate.
- If information is missing or unclear, state that clearly.
- Avoid personalized financial advice; keep recommendations informational (Buy/Hold/Sell style only).
""",

    expected_output="""
Return the answer in the following markdown structure exactly:

### Key Metrics
- name: <metric name>, value: <value>, unit: <unit or ->, evidence: "<short quote>"
- ... 2-10 items

### Investment Overview
- stance: <Buy|Hold|Sell>
- rationale: <1-3 short bullets grounded in evidence>
- signals: <2-6 compact signals>
- assumptions: <1-3 short assumptions>

### Risk Assessment
- score: <1-5>
- factors: <2-6 factors driving the score>
- confidence: <low|medium|high>
""",

    agent=financial_analyst,
    tools=[
        read_financial_document_tool,
        analyze_investment_tool,
        risk_assessment_tool,
        # search tool is optional; include for context lookup if needed
        search_tool,
    ],
    async_execution=False,
)

## Creating an investment analysis task
investment_analysis = Task(
    description="""
Using text extracted from {file_path}, produce a concise, non-personalized investment analysis relevant to {query}.
Ground the analysis in detected metrics and transparent heuristics; list assumptions and uncertainties.
""",

    expected_output="""
Return the answer in this markdown structure:

### Investment Overview
- stance: <Buy|Hold|Sell>
- rationale: <1-3 short bullets>
- signals: <2-6 compact signals>
- assumptions: <1-3 short assumptions>
- uncertainties: <1-3 short uncertainties>

### Detected Metrics
- name: <metric>, value: <value>, unit: <unit or ->
- ... 1-8 items
""",

    agent=investment_advisor,
    tools=[
        read_financial_document_tool,
        analyze_investment_tool,
    ],
    async_execution=False,
)

## Creating a risk assessment task
risk_assessment = Task(
    description="""
Assess risk based on text extracted from {file_path} with respect to {query}.
Use simple, transparent heuristics and avoid speculation. Indicate confidence when evidence is thin.
""",

    expected_output="""
Return the answer in this markdown structure:

### Risk Assessment
- score: <1-5>
- factors: <2-6 concise factors grounded in evidence>
- confidence: <low|medium|high>
""",

    agent=risk_assessor,
    tools=[
        read_financial_document_tool,
        risk_assessment_tool,
    ],
    async_execution=False,
)

    
verification = Task(
    description="""
Verify whether {file_path} contains financial context. Extract text and check for financial indicators (e.g., revenue, EBITDA, cash flow, assets, liabilities).
Favor precision over recall to avoid false positives; when uncertain, state uncertainty.
""",

    expected_output="""
Return the answer in this markdown structure:

### Verification
- appears_financial: <yes|no|uncertain>
- terms_found: <up to 5 indicative terms>
- note: <short clarification if uncertain>
""",

    agent=verifier,
    tools=[read_financial_document_tool],
    async_execution=False
)