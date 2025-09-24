## Importing libraries and files
from crewai import Agent, LLM
from config import settings

from tools import (
    search_tool,
    read_financial_document_tool,
    analyze_investment_tool,
    risk_assessment_tool,
)

### Loading LLM
# Use centralized settings for model selection
llm = LLM(model=settings.LLM_MODEL)

# Financial Analyst agent (professional, cautious, evidence-driven)
financial_analyst = Agent(
    role="Senior Financial Analyst",
    goal=(
        "Analyze provided financial documents and the user's query: {query}. "
        "Extract relevant metrics, reason cautiously, and produce a concise, "
        "evidence-based summary. Avoid speculative or personalized investment advice."
    ),
    verbose=True,
    memory=False,
    backstory=(
        "An experienced analyst focused on clear, compliant, and data-driven analysis. "
        "Skilled at reading financial statements, identifying key metrics, and "
        "communicating findings responsibly."
    ),
    tools=[
        search_tool,
        read_financial_document_tool,
        analyze_investment_tool,
        risk_assessment_tool,
    ],
    llm=llm,
    max_iter=3,
    max_rpm=30,
    allow_delegation=True
)

# Document verifier agent (checks for financial context only)
verifier = Agent(
    role="Financial Document Verifier",
    goal=(
        "Verify whether the provided file at the path appears to contain financial "
        "context by extracting text and checking for financial terms."
    ),
    verbose=True,
    memory=False,
    backstory=(
        "Detail-oriented reviewer who assesses documents for financial relevance. "
        "Ensures we only proceed with files that exhibit financial indicators."
    ),
    llm=llm,
    tools=[
        read_financial_document_tool,
    ],
    max_iter=2,
    max_rpm=30,
    allow_delegation=False
)


# Investment analysis specialist (non-personalized, heuristic-based)
investment_advisor = Agent(
    role="Investment Analysis Specialist",
    goal=(
        "From extracted text, derive a compact, non-personalized investment overview "
        "using simple heuristics. Clearly state assumptions and uncertainties."
    ),
    verbose=True,
    backstory=(
        "Provides structured, metrics-driven investment overviews without offering "
        "personalized financial advice."
    ),
    llm=llm,
    tools=[
        read_financial_document_tool,
        analyze_investment_tool,
        search_tool,
    ],
    max_iter=2,
    max_rpm=30,
    allow_delegation=False
)


# Risk assessment specialist
risk_assessor = Agent(
    role="Risk Assessment Specialist",
    goal=(
        "Generate a concise risk assessment based on extracted metrics and simple "
        "rules-of-thumb. Provide a risk score with clear contributing factors."
    ),
    verbose=True,
    backstory=(
        "Evaluates leverage, liquidity, profitability, and growth to gauge risk in "
        "a transparent, reproducible manner."
    ),
    llm=llm,
    tools=[
        read_financial_document_tool,
        risk_assessment_tool,
        search_tool,
    ],
    max_iter=2,
    max_rpm=30,
    allow_delegation=False
)
