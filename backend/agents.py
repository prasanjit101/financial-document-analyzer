## Importing libraries and files
from crewai import Agent, LLM
from config import settings

from tools import (
    read_financial_document_tool,
    analyze_investment_tool,
    risk_assessment_tool,
)

# Get LLM instance
def get_llm(model: str = settings.LLM_MODEL):
    return LLM(
        model=model,
    )

# Financial Document Verifier (first line of defense)
verifier = Agent(
    role="Financial Document Verifier",
    goal=(
        "Confirm whether {file_path} is a financial document before any further analysis. "
        "If indicators are absent, clearly state 'non-financial' and instruct the crew to halt downstream steps."
    ),
    verbose=settings.APP_ENV == "dev",
    backstory=(
        "Meticulous reviewer charged with filtering irrelevant documents so later agents stay focused on valid financial materials."
    ),
    llm=get_llm(),
    tools=[
        read_financial_document_tool,
    ],
    cache=True,
    max_iter=4,
    max_rpm=30,
    allow_delegation=False,
)


# Financial Analyst (core metrics extraction)
financial_analyst = Agent(
    role="Senior Financial Analyst",
    goal=(
        "Transform verified financial text into structured metrics, ratios, and trend commentary for the crew. "
        "Respect verification outcomes—if the verifier flags the document as non-financial, respond with a short termination notice."
    ),
    verbose=settings.APP_ENV == "dev",
    backstory=(
        "Seasoned analyst who converts raw filings into actionable datasets, feeding downstream risk and investment work."
    ),
    llm=get_llm(),
    tools=[
        read_financial_document_tool,
    ],
    max_iter=4,
    max_rpm=30,
    allow_delegation=False,
)


# Risk Assessor (leverages analyst output)
risk_assessor = Agent(
    role="Risk Assessment Specialist",
    goal=(
        "Digest the financial analyst's structured output and compute an evidence-backed risk profile. "
        "Use the risk tool to quantify exposure, highlight vulnerabilities, and note stress scenarios."
    ),
    verbose=settings.APP_ENV == "dev",
    backstory=(
        "Pragmatic risk manager skilled at interpreting ratios, liquidity markers, and leverage signals provided by colleagues."
    ),
    llm=get_llm(),
    tools=[
        risk_assessment_tool,
    ],
    max_iter=3,
    max_rpm=30,
    allow_delegation=False,
)


# Investment Advisor (final synthesis)
investment_advisor = Agent(
    role="Investment Analysis Specialist",
    goal=(
        "Fuse verification, financial analysis, and risk outputs into an informational Buy/Hold/Sell style briefing. "
        "Ensure every claim is traceable to upstream evidence and remain non-personalized."
    ),
    verbose=settings.APP_ENV == "dev",
    backstory=(
        "Advises stakeholders by translating collective findings into concise investment theses without giving personalized advice."
    ),
    llm=get_llm(),
    tools=[
        analyze_investment_tool,
    ],
    max_iter=3,
    max_rpm=30,
    allow_delegation=False,
)
