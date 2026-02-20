"""Prompt templates for equity research analysis tasks."""

from __future__ import annotations

from pydantic import BaseModel

from app.services.llm.types import LLMMessage, LLMRole, TaskType


class PromptTemplate(BaseModel):
    """A reusable prompt template for LLM requests.

    Templates define the system prompt and user message structure for
    specific analysis tasks.
    """

    name: str
    task_type: TaskType
    system_prompt: str
    user_template: str  # Has {placeholders} for dynamic data
    version: str = "1.0"

    def render(self, **kwargs) -> list[LLMMessage]:
        """Render template into LLMMessage list.

        Args:
            **kwargs: Values to substitute into user_template placeholders

        Returns:
            List of LLMMessage objects ready for API calls

        Raises:
            KeyError: If a required placeholder is not provided
        """
        messages = [
            LLMMessage(role=LLMRole.SYSTEM, content=self.system_prompt),
            LLMMessage(role=LLMRole.USER, content=self.user_template.format(**kwargs)),
        ]
        return messages


# =============================================================================
# System Prompts
# =============================================================================

_ANALYST_SYSTEM_PROMPT = """You are an expert equity research analyst with deep expertise in financial statement analysis, valuation methodologies, and capital markets. Your analysis is:

1. **Evidence-Based**: Every claim is supported by specific data points or documented sources
2. **Balanced**: You consider both bull and bear cases objectively
3. **Precise**: You use accurate financial terminology and quantitative reasoning
4. **Actionable**: Your insights directly inform investment decisions

Your role is to synthesize complex information into clear, investment-relevant insights that institutional investors can trust."""

_VALUATION_SYSTEM_PROMPT = """You are a valuation specialist focusing on DCF, relative valuation, and market multiples. You:

1. Understand the appropriate valuation methodology for each industry and business model
2. Identify key value drivers and sensitivities
3. Use conservative assumptions with clear rationale
4. Provide ranges rather than single-point estimates when appropriate

Your output should be ready for inclusion in professional equity research reports."""


# =============================================================================
# Template Definitions
# =============================================================================

def get_thesis_generation_template() -> PromptTemplate:
    """Template for generating initial investment thesis.

    Placeholders:
    - ticker: Stock ticker symbol
    - company_name: Full company name
    - business_description: Description of business model and operations
    - key_metrics: Key financial metrics (market cap, revenue, margins, etc.)
    - recent_news: Recent news and developments
    - industry_context: Industry trends and competitive positioning

    Returns:
        PromptTemplate for thesis generation
    """
    return PromptTemplate(
        name="thesis_generation",
        task_type=TaskType.THESIS_GENERATION,
        system_prompt=_ANALYST_SYSTEM_PROMPT + """

**Task**: Generate a comprehensive investment thesis for the stock.

Your thesis should include:
1. **Investment Thesis Summary**: 2-3 sentences capturing the core bull/bear view
2. **Investment Thesis**: 4-6 key points explaining why the stock will outperform/underperform
3. **Key Growth Drivers**: What will drive revenue/earnings growth
4. **Key Risks**: Main risks to the thesis (both company-specific and macro)
5. **Catalysts**: Events that could drive stock re-rating
6. **Valuation Context**: How the market currently values the stock vs. intrinsic value
7. **Recommendation**: Buy/Hold/Sell with conviction level (High/Medium/Low)

Format your response in clean markdown with clear headings.""",
        user_template="""Generate an investment thesis for:

**Company**: {ticker} - {company_name}

**Business Overview**:
{business_description}

**Key Financial Metrics**:
{key_metrics}

**Recent Developments**:
{recent_news}

**Industry Context**:
{industry_context}

Please provide a comprehensive investment thesis with clear recommendation and conviction level.""",
        version="1.0",
    )


def get_thesis_update_template() -> PromptTemplate:
    """Template for updating an existing investment thesis.

    Placeholders:
    - ticker: Stock ticker symbol
    - existing_thesis: The current investment thesis
    - new_information: New data, earnings, news, or developments
    - time_elapsed: Time since thesis was last updated

    Returns:
        PromptTemplate for thesis updates
    """
    return PromptTemplate(
        name="thesis_update",
        task_type=TaskType.THESIS_UPDATE,
        system_prompt=_ANALYST_SYSTEM_PROMPT + """

**Task**: Update an existing investment thesis based on new information.

Your update should:
1. Assess whether the new information confirms or challenges the existing thesis
2. Identify specific changes to the bull/bear case
3. Update key assumptions if warranted
4. Re-evaluate the investment recommendation
5. Highlight what, if anything, has materially changed

Be explicit about what changed and what stayed the same.""",
        user_template="""Update the investment thesis for {ticker} based on new information.

**Existing Thesis**:
{existing_thesis}

**New Information**:
{new_information}

**Time Since Last Update**: {time_elapsed}

Please update the thesis, highlighting what has changed and reassessing the recommendation.""",
        version="1.0",
    )


def get_news_analysis_template() -> PromptTemplate:
    """Template for analyzing news impact on a stock.

    Placeholders:
    - ticker: Stock ticker symbol
    - news_headline: News article headline
    - news_content: Full text or summary of the news article
    - current_thesis: Current investment thesis (for alignment assessment)
    - publication_date: When the news was published

    Returns:
        PromptTemplate for news analysis
    """
    return PromptTemplate(
        name="news_analysis",
        task_type=TaskType.NEWS_ANALYSIS,
        system_prompt=_ANALYST_SYSTEM_PROMPT + """

**Task**: Analyze a news article's impact on a stock.

Your analysis should include:
1. **Relevance**: How relevant is this news to the investment thesis? (High/Medium/Low)
2. **Sentiment**: Positive, negative, or neutral for the stock? Why?
3. **Financial Impact**: Estimate the magnitude of financial impact (if quantifiable)
4. **Thesis Alignment**: Does this confirm or challenge the existing thesis?
5. **Action Required**: Does this warrant immediate action (thesis update, position review)?
6. **Key Takeaways**: 2-3 bullet points on what matters most

Be concise and direct.""",
        user_template="""Analyze the following news for {ticker}:

**Headline**: {news_headline}

**Content**: {news_content}

**Publication Date**: {publication_date}

**Current Thesis**:
{current_thesis}

Assess relevance, sentiment, financial impact, and whether this warrants any action.""",
        version="1.0",
    )


def get_assumption_generation_template() -> PromptTemplate:
    """Template for generating financial assumptions for DCF modeling.

    Placeholders:
    - ticker: Stock ticker symbol
    - company_name: Full company name
    - business_description: Business model and operations
    - historical_financials: Historical revenue, margins, growth rates
    - industry_trends: Industry growth rates and trends
    - guidance: Company guidance (if available)

    Returns:
        PromptTemplate for assumption generation
    """
    return PromptTemplate(
        name="assumption_generation",
        task_type=TaskType.ASSUMPTION_GENERATION,
        system_prompt=_VALUATION_SYSTEM_PROMPT + """

**Task**: Generate base-case financial assumptions for a DCF valuation.

Your assumptions should cover:
1. **Revenue Growth**: Year-by-year growth rates (years 1-5, then terminal)
2. **Operating Margins**: Target EBIT/EBITDA margins with ramp schedule
3. **WACC / Discount Rate**: Appropriate cost of capital for this business
4. **Terminal Growth Rate**: Conservative long-term growth assumption
5. **Capital Expenditure**: Capex as % of revenue
6. **Working Capital**: Working capital assumptions
7. **Tax Rate**: Effective tax rate assumption

Provide your assumptions in a structured format with clear rationale for each.""",
        user_template="""Generate DCF assumptions for {ticker} ({company_name}):

**Business Overview**:
{business_description}

**Historical Financials**:
{historical_financials}

**Industry Context**:
{industry_trends}

**Company Guidance**:
{guidance}

Please provide a complete set of base-case assumptions for a 5-year DCF model.""",
        version="1.0",
    )


def get_company_comparison_template() -> PromptTemplate:
    """Template for comparing two companies.

    Placeholders:
    - ticker_a: First company ticker
    - company_a_name: First company name
    - company_a_metrics: Key metrics for company A
    - ticker_b: Second company ticker
    - company_b_name: Second company name
    - company_b_metrics: Key metrics for company B
    - comparison_focus: Specific aspects to compare (valuation, growth, profitability, etc.)

    Returns:
        PromptTemplate for company comparison
    """
    return PromptTemplate(
        name="company_comparison",
        task_type=TaskType.COMPANY_COMPARISON,
        system_prompt=_ANALYST_SYSTEM_PROMPT + """

**Task**: Compare two companies across key dimensions.

Your comparison should be:
1. **Quantitative**: Side-by-side metrics with actual numbers
2. **Qualitative**: Business model, competitive position, management quality
3. **Valuation**: How each company is valued relative to peers and growth
4. **Investment Merit**: Which represents the better opportunity and why?

Be fair and objective—acknowledge strengths and weaknesses of both.""",
        user_template="""Compare {ticker_a} ({company_a_name}) vs {ticker_b} ({company_b_name}):

**{company_a_name} Metrics**:
{company_a_metrics}

**{company_b_name} Metrics**:
{company_b_metrics}

**Comparison Focus**: {comparison_focus}

Please provide a detailed comparison with tables for key metrics and a clear investment conclusion.""",
        version="1.0",
    )


def get_note_extraction_template() -> PromptTemplate:
    """Template for extracting structured data from analyst notes.

    Placeholders:
    - note_text: Free-text analyst notes or research commentary
    - extraction_fields: List of fields to extract (price targets, ratings, etc.)

    Returns:
        PromptTemplate for note extraction
    """
    return PromptTemplate(
        name="note_extraction",
        task_type=TaskType.NOTE_EXTRACTION,
        system_prompt="""You are a data extraction specialist for financial research.

Your task is to extract structured data from unstructured analyst notes.
Extract ONLY information that is explicitly stated in the text.
If a specific data point is not mentioned, return null rather than guessing.

Output your results in JSON format with the requested fields.""",
        user_template="""Extract the following fields from the analyst note below:

**Fields to Extract**: {extraction_fields}

**Analyst Note**:
{note_text}

Please extract the data in JSON format.""",
        version="1.0",
    )


def get_watch_items_template() -> PromptTemplate:
    """Template for generating watch items and catalysts.

    Placeholders:
    - ticker: Stock ticker symbol
    - company_name: Full company name
    - investment_thesis: Current investment thesis
    - upcoming_events: Known upcoming events (earnings, presentations, etc.)

    Returns:
        PromptTemplate for watch items generation
    """
    return PromptTemplate(
        name="watch_items",
        task_type=TaskType.WATCH_ITEMS,
        system_prompt=_ANALYST_SYSTEM_PROMPT + """

**Task**: Generate watch items and catalysts for monitoring a stock.

Your output should include:
1. **Key Metrics to Watch**: Specific KPIs or metrics that matter most
2. **Upcoming Catalysts**: Events that could move the stock (earnings, product launches, etc.)
3. **Red Flags**: Warning signs that would indicate thesis deterioration
4. **Green Flags**: Positive signs that would confirm the thesis
5. **Monitoring Frequency**: How often to check each item (daily, weekly, quarterly)

Focus on high-impact, actionable items.""",
        user_template="""Generate watch items for {ticker} ({company_name}):

**Current Investment Thesis**:
{investment_thesis}

**Known Upcoming Events**:
{upcoming_events}

Please list the key items to monitor, with specific metrics and thresholds where relevant.""",
        version="1.0",
    )
