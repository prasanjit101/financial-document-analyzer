## Importing libraries and files
from crewai import Task

from agents import financial_analyst, verifier, investment_advisor, risk_assessor
from tools import (
    read_financial_document_tool,
    analyze_investment_tool,
    risk_assessment_tool,
)

## Sequential crew tasks following the verifier → analyst → risk → advisor flow
analyze_financial_document = Task(
    description="""
Use the verified document at {file_path} to build the structured financial package needed by the crew.

Workflow:
1. Call the PDF reader tool to obtain JSON containing text, detected metrics, and classification.
2. If the verification output signalled `halt_pipeline: true`, produce a two-line response: "### Structured Financial Data" followed by "- status: halted (non-financial document)" and stop.
3. Extract concrete metrics (revenue, EBITDA, margins, cash flow, assets, liabilities, growth rates) with units and short evidence quotes.
4. Derive key ratios (liquidity, profitability, leverage) when possible; note calculation assumptions.
5. Summarize notable trends and preliminary insights that the risk assessor and investment advisor should know.
6. Provide a machine-readable data package to enable downstream tools to reuse your findings.

Rules:
- Depend only on tool outputs or verified text—no speculation.
- Highlight gaps or uncertainties explicitly.
- Maintain non-personalized language throughout.
""",

    expected_output="""
Return the answer in this markdown structure:

### Structured Financial Data
- status: <ok|halted>
- classification: <balance_sheet|income_statement|cash_flow_statement|financial|unknown>
- page_count: <number>
- indicators: <comma-separated key terms or ->

### Key Metrics
- name: <metric>, value: <value>, unit: <unit or ->, evidence: "<short quote>"
- ... at least 3 items when available

### Calculated Ratios
- name: <ratio>, value: <value>, basis: <inputs or ->, note: <assumption/limitation>
- ... 1-5 items (omit section if none)

### Trends & Insights
- <one sentence trend grounded in evidence>
- ... 2-4 bullets capturing momentum, seasonality, or anomalies

### Data Package
```json
{
  "metrics": [...],
  "ratios": [...],
  "insights": [...],
  "classification": "<string>",
  "indicators": [...]
}
```
""",

    agent=financial_analyst,
    tools=[
        read_financial_document_tool,
    ],
    async_execution=False,
)

risk_assessment = Task(
    description="""
Produce a concise risk assessment for {file_path} leveraging the structured data created by the financial analyst.

Workflow:
1. Inspect analyst outputs for metrics, ratios, and trends; combine with verification status.
2. If the analyst reported `status: halted`, mirror that status and skip further analysis.
3. Call the risk assessment tool with the analyst data plus any relevant excerpts to compute an evidence-backed risk profile.
4. Enumerate risk factors, mitigating elements, and recommended stress scenarios.
5. Set confidence according to data depth and clarity.

Rules:
- Keep scoring transparent and reference the inputs used.
- Limit to concise, actionable language.
- Avoid speculative commentary; note data gaps explicitly.
""",

    expected_output="""
Return the answer in this markdown structure:

### Risk Profile
- score: <1-5>
- confidence: <low|medium|high>
- status: <ok|halted>

### Risk Factors
- <factor grounded in evidence>
- ... 2-6 bullets

### Mitigants & Monitoring
- <mitigating element or monitoring directive>
- ... 1-4 bullets

### Stress Tests
- <scenario to model>
- ... 1-3 entries

### Data Package
```json
{
  "score": <number>,
  "confidence": "<string>",
  "factors": [...],
  "mitigants": [...],
  "stress_tests": [...]
}
```
""",

    agent=risk_assessor,
    tools=[
        risk_assessment_tool,
    ],
    async_execution=False,
)

investment_analysis = Task(
    description="""
Synthesize a final investment briefing using the financial analyst and risk assessor outputs for {file_path} relative to {query}.

Workflow:
1. Review the verification, structured financial data, and risk profile results produced earlier.
2. If any prior step set `status: halted` or `halt_pipeline: true`, echo that status and terminate with a short note.
3. Call the investment analysis tool with the combined context to generate quantitative support.
4. Translate all evidence into an informational Buy/Hold/Sell style overview, keeping recommendations non-personalized.
5. Capture key supporting signals, assumptions, and open questions for human follow-up.

Rules:
- Every statement must be backed by upstream evidence or tool output.
- Use concise bullets and avoid redundant commentary.
- If uncertainty dominates, lean toward Hold and articulate why.

""",

    expected_output="""
Return the answer in the following Markdown format:

# stance
<Buy|Hold|Sell>

## Signals
- <signal 1>
- <signal 2>
- ...

## Assumptions
- <assumption 1>
- <assumption 2>
- ...

## Uncertainties
- <uncertainty 1>
- <uncertainty 2>
- ...
""",

    agent=investment_advisor,
    tools=[
        analyze_investment_tool,
    ],
    async_execution=False,
)

verification = Task(
    description="""
Verify whether {file_path} contains financial context before the crew proceeds.

Workflow:
1. Call the PDF reader tool to extract structured JSON.
2. Determine whether the document is financial using detected indicators; classify the document type when possible.
3. If non-financial, set `halt_pipeline: true` and provide a short explanation to stop downstream agents.
4. When uncertain, mark `appears_financial: uncertain` and describe the ambiguity.
""",

    expected_output="""
Return the answer in this markdown structure:

### Verification
- appears_financial: <yes|no|uncertain>
- document_type: <balance_sheet|income_statement|cash_flow_statement|financial|unknown>
- indicators: <up to 5 indicative terms or ->
- halt_pipeline: <true|false>
- note: <short clarification or reason for halt>
""",

    agent=verifier,
    tools=[read_financial_document_tool],
    async_execution=False,
)