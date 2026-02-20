"""
Canonical financial data schemas.

These Pydantic models are the shared contract between ALL data providers.
Every provider normalizes its API responses into these models.
"""
from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field

# =============================================================================
# Line Item Taxonomy
# =============================================================================

class LineItem(str, Enum):
    """Canonical financial line items all providers must map to."""

    # Income Statement
    REVENUE = "revenue"
    COST_OF_REVENUE = "cost_of_revenue"
    GROSS_PROFIT = "gross_profit"
    RD_EXPENSE = "research_and_development"
    SGA_EXPENSE = "selling_general_admin"
    TOTAL_OPEX = "total_operating_expenses"
    OPERATING_INCOME = "operating_income"
    EBITDA = "ebitda"
    DA = "depreciation_amortization"
    INTEREST_EXPENSE = "interest_expense"
    INCOME_BEFORE_TAX = "income_before_tax"
    TAX_EXPENSE = "income_tax_expense"
    NET_INCOME = "net_income"
    EPS = "eps"
    EPS_DILUTED = "eps_diluted"

    # Balance Sheet
    CASH = "cash_and_equivalents"
    SHORT_TERM_INVESTMENTS = "short_term_investments"
    ACCOUNTS_RECEIVABLE = "accounts_receivable"
    INVENTORY = "inventory"
    TOTAL_CURRENT_ASSETS = "total_current_assets"
    PP_AND_E = "property_plant_equipment"
    GOODWILL = "goodwill"
    INTANGIBLES = "intangible_assets"
    TOTAL_ASSETS = "total_assets"
    ACCOUNTS_PAYABLE = "accounts_payable"
    SHORT_TERM_DEBT = "short_term_debt"
    TOTAL_CURRENT_LIABILITIES = "total_current_liabilities"
    LONG_TERM_DEBT = "long_term_debt"
    TOTAL_LIABILITIES = "total_liabilities"
    TOTAL_EQUITY = "total_stockholders_equity"
    SHARES_OUTSTANDING = "shares_outstanding"

    # Cash Flow
    OPERATING_CASH_FLOW = "operating_cash_flow"
    CAPEX = "capital_expenditure"
    FREE_CASH_FLOW = "free_cash_flow"
    DIVIDENDS_PAID = "dividends_paid"
    SHARE_BUYBACKS = "share_repurchase"
    FINANCING_CASH_FLOW = "financing_cash_flow"
    INVESTING_CASH_FLOW = "investing_cash_flow"

    # Ratios / Valuation
    PE_RATIO = "pe_ratio"
    EV_EBITDA = "ev_to_ebitda"
    PRICE_TO_BOOK = "price_to_book"
    PRICE_TO_SALES = "price_to_sales"
    ROE = "return_on_equity"
    ROA = "return_on_assets"
    ROIC = "return_on_invested_capital"
    GROSS_MARGIN = "gross_margin"
    OPERATING_MARGIN = "operating_margin"
    NET_MARGIN = "net_margin"
    DEBT_TO_EQUITY = "debt_to_equity"
    CURRENT_RATIO = "current_ratio"
    FCF_YIELD = "fcf_yield"


class PeriodType(str, Enum):
    ANNUAL = "annual"
    QUARTERLY = "quarterly"


class StatementType(str, Enum):
    INCOME = "income"
    BALANCE_SHEET = "balance_sheet"
    CASH_FLOW = "cash_flow"


# =============================================================================
# Canonical Financial Data Models
# =============================================================================

class IncomeStatement(BaseModel):
    """Normalized income statement — all providers map to this."""
    ticker: str
    period_date: date
    period_type: PeriodType
    currency: str = "USD"
    revenue: Optional[float] = None
    cost_of_revenue: Optional[float] = None
    gross_profit: Optional[float] = None
    research_and_development: Optional[float] = None
    selling_general_admin: Optional[float] = None
    total_operating_expenses: Optional[float] = None
    operating_income: Optional[float] = None
    ebitda: Optional[float] = None
    depreciation_amortization: Optional[float] = None
    interest_expense: Optional[float] = None
    income_before_tax: Optional[float] = None
    income_tax_expense: Optional[float] = None
    net_income: Optional[float] = None
    eps: Optional[float] = None
    eps_diluted: Optional[float] = None
    shares_outstanding: Optional[float] = None
    shares_diluted: Optional[float] = None
    source: str  # e.g. "fmp", "finnhub", "yfinance"
    fetched_at: datetime = Field(default_factory=datetime.utcnow)


class BalanceSheet(BaseModel):
    """Normalized balance sheet."""
    ticker: str
    period_date: date
    period_type: PeriodType
    currency: str = "USD"
    cash_and_equivalents: Optional[float] = None
    short_term_investments: Optional[float] = None
    accounts_receivable: Optional[float] = None
    inventory: Optional[float] = None
    total_current_assets: Optional[float] = None
    property_plant_equipment: Optional[float] = None
    goodwill: Optional[float] = None
    intangible_assets: Optional[float] = None
    total_assets: Optional[float] = None
    accounts_payable: Optional[float] = None
    short_term_debt: Optional[float] = None
    total_current_liabilities: Optional[float] = None
    long_term_debt: Optional[float] = None
    total_liabilities: Optional[float] = None
    total_stockholders_equity: Optional[float] = None
    shares_outstanding: Optional[float] = None
    source: str
    fetched_at: datetime = Field(default_factory=datetime.utcnow)


class CashFlow(BaseModel):
    """Normalized cash flow statement."""
    ticker: str
    period_date: date
    period_type: PeriodType
    currency: str = "USD"
    operating_cash_flow: Optional[float] = None
    capital_expenditure: Optional[float] = None
    free_cash_flow: Optional[float] = None
    dividends_paid: Optional[float] = None
    share_repurchase: Optional[float] = None
    financing_cash_flow: Optional[float] = None
    investing_cash_flow: Optional[float] = None
    source: str
    fetched_at: datetime = Field(default_factory=datetime.utcnow)


class StockQuote(BaseModel):
    """Real-time or near-real-time stock quote."""
    ticker: str
    price: float
    change: Optional[float] = None
    change_percent: Optional[float] = None
    volume: Optional[int] = None
    market_cap: Optional[float] = None
    high: Optional[float] = None
    low: Optional[float] = None
    open: Optional[float] = None
    previous_close: Optional[float] = None
    timestamp: datetime
    source: str


class PriceBar(BaseModel):
    """Single OHLCV price bar."""
    ticker: str
    date: date
    open: float
    high: float
    low: float
    close: float
    volume: int
    adjusted_close: Optional[float] = None
    source: str


class CompanyProfile(BaseModel):
    """Company information and classification."""
    ticker: str
    company_name: str
    exchange: Optional[str] = None
    sector: Optional[str] = None
    industry: Optional[str] = None
    market_cap: Optional[float] = None
    description: Optional[str] = None
    website: Optional[str] = None
    ceo: Optional[str] = None
    country: Optional[str] = None
    employees: Optional[int] = None
    ipo_date: Optional[date] = None
    source: str
    fetched_at: datetime = Field(default_factory=datetime.utcnow)


class FinancialRatios(BaseModel):
    """Pre-computed financial ratios."""
    ticker: str
    pe_ratio: Optional[float] = None
    ev_to_ebitda: Optional[float] = None
    price_to_book: Optional[float] = None
    price_to_sales: Optional[float] = None
    return_on_equity: Optional[float] = None
    return_on_assets: Optional[float] = None
    return_on_invested_capital: Optional[float] = None
    gross_margin: Optional[float] = None
    operating_margin: Optional[float] = None
    net_margin: Optional[float] = None
    debt_to_equity: Optional[float] = None
    current_ratio: Optional[float] = None
    fcf_yield: Optional[float] = None
    dividend_yield: Optional[float] = None
    peg_ratio: Optional[float] = None
    source: str
    fetched_at: datetime = Field(default_factory=datetime.utcnow)


class NewsItem(BaseModel):
    """Financial news article with optional sentiment."""
    headline: str
    summary: Optional[str] = None
    source_name: str
    source_url: Optional[str] = None
    ticker: Optional[str] = None
    published_at: datetime
    sentiment_score: Optional[float] = None  # -1.0 to 1.0
    sentiment_label: Optional[str] = None    # positive, negative, neutral
    relevance_score: Optional[float] = None  # 0.0 to 1.0
    source: str
    fetched_at: datetime = Field(default_factory=datetime.utcnow)


class TickerSearchResult(BaseModel):
    """Search result when looking up tickers."""
    ticker: str
    name: str
    exchange: Optional[str] = None
    type: Optional[str] = None  # stock, etf, etc.
