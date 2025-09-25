## Importing libraries and files
from crewai import Agent, LLM
from config import settings

from tools import (
    search_tool,
    read_financial_document_tool,
    analyze_investment_tool,
    risk_assessment_tool,
)

# Get LLM instance
def get_llm(model: str = settings.LLM_MODEL):
    return LLM(
        model=model,
        # api_key=settings.LANGDB_API_KEY,
        # base_url=settings.LANGDB_API_BASE_URL,
        # extra_headers={"x-project-id": settings.LANGDB_PROJECT_ID}
        )

# Financial Analyst agent (professional, cautious, evidence-driven)
financial_analyst = Agent(
    role="Senior Financial Analyst",
    goal=(
        "You are a precise, compliance-aware financial analyst. "
        "Analyze the provided document(s) and the user's query {query}. "
        "Extract concrete metrics strictly from tool outputs, attribute claims to the source text, "
        "and produce a concise, structured, evidence-based analysis. "
        "Never provide personalized investment advice. If information is missing, say so."
    ),
    verbose=True,
    backstory=(
        "Experienced analyst focused on clear, compliant, data-driven analysis. "
        "Strong at reading financial statements, identifying key metrics, and communicating responsibly."
    ),
    tools=[
        search_tool,
        read_financial_document_tool,
        analyze_investment_tool,
        risk_assessment_tool,
    ],
    llm=get_llm("gemini/gemini-2.5-pro"),
    max_iter=3, 
    max_rpm=30,
    allow_delegation=True
)

# Document verifier agent (checks for financial context only)
verifier = Agent(
    role="Financial Document Verifier",
    goal=(
        "Determine whether the file at {file_path} plausibly contains financial context. "
        "Use tools to extract text and look for financial indicators (e.g., revenue, EBITDA, cash flow, assets, liabilities). "
        "Avoid over-claiming when signals are weak; when uncertain, state uncertainty explicitly."
    ),
    verbose=True,
    backstory=(
        "Detail-oriented reviewer who filters non-financial documents to save downstream effort."
    ),
    llm=get_llm(),
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
        "From extracted text, produce a compact, non-personalized investment overview. "
        "Base all points on detected metrics and transparent heuristics; list assumptions and uncertainties. "
        "Express any recommendation in broad, informational terms (e.g., Buy/Hold/Sell style) without personalization."
    ),
    verbose=True,
    backstory=(
        "Provides structured, metrics-driven investment overviews without personalized advice."
    ),
    llm=get_llm(),
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
        "Generate a concise, reproducible risk assessment grounded in extracted metrics and simple rules-of-thumb. "
        "Output a numerical risk score and list concrete contributing factors. "
        "If evidence is insufficient, indicate low confidence instead of guessing."
    ),
    verbose=True,
    backstory=(
        "Evaluates leverage, liquidity, profitability, and growth using transparent heuristics."
    ),
    llm=get_llm(),
    tools=[
        read_financial_document_tool,
        risk_assessment_tool,
        search_tool,
    ],
    max_iter=2,
    max_rpm=30,
    allow_delegation=False
)
