## Importing libraries and files
from crewai import Task

from agents import financial_analyst, verifier, investment_advisor, risk_assessor
from tools import search_tool, FinancialDocumentTool, InvestmentTool, RiskTool

## Creating a task to help solve user's query
analyze_financial_document = Task(
    description="""
Use the provided financial document at {file_path} to:
- Extract text using the PDF reader tool
- Identify key metrics present in the text
- Summarize a non-personalized investment outlook
- Provide a concise risk assessment
Also consider the user's query: {query}. Avoid personalized financial advice.
""",

    expected_output="""
Return a structured analysis including:
- Summary of key metrics detected (values if present)
- Investment overview (Buy/Hold/Sell style, with brief rationale and signals)
- Risk score (1-5) with contributing factors
""",

    agent=financial_analyst,
    tools=[
        FinancialDocumentTool.read_data_tool,
        InvestmentTool.analyze_investment_tool,
        RiskTool.create_risk_assessment_tool,
        # search tool is optional; include for context lookup if needed
        search_tool,
    ],
    async_execution=False,
)

## Creating an investment analysis task
investment_analysis = Task(
    description="""
From text extracted from {file_path}, perform a concise, non-personalized investment analysis relevant to: {query}.
""",

    expected_output="""
Provide a compact overview including:
- Recommendation (Buy/Hold/Sell style)
- Score and 2-6 key signals
- Any detected key metrics with values
""",

    agent=investment_advisor,
    tools=[
        FinancialDocumentTool.read_data_tool,
        InvestmentTool.analyze_investment_tool,
    ],
    async_execution=False,
)

## Creating a risk assessment task
risk_assessment = Task(
    description="""
Assess risk based on text extracted from {file_path}. Consider query context: {query}.
""",

    expected_output="""
Return risk score (1-5) and list of key risk factors found in the text.
""",

    agent=risk_assessor,
    tools=[
        FinancialDocumentTool.read_data_tool,
        RiskTool.create_risk_assessment_tool,
    ],
    async_execution=False,
)

    
verification = Task(
    description="""
Verify that {file_path} contains financial context by extracting text and checking for key terms. Avoid false positives.
""",

    expected_output="""
State whether the document appears financial and list a few detected financial terms if any. If uncertain, say so explicitly.
""",

    agent=verifier,
    tools=[FinancialDocumentTool.read_data_tool],
    async_execution=False
)