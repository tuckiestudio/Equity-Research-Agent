"""
yfinance data provider implementation.

https://github.com/ranaroussi/yfinance

Implements FundamentalsProvider, PriceProvider, and ProfileProvider protocols.
Uses asyncio.to_thread to wrap synchronous yfinance calls.
"""
from __future__ import annotations

import asyncio
from datetime import date, datetime, timedelta
from typing import Optional
import xml.etree.ElementTree as ET

import httpx

from app.core.errors import ProviderError
from app.core.logging import get_logger
from app.schemas.financial import (
    BalanceSheet,
    CashFlow,
    CompanyProfile,
    FinancialRatios,
    IncomeStatement,
    NewsItem,
    PeriodType,
    PriceBar,
    StockQuote,
    TickerSearchResult,
)


class YFinanceProvider:
    """
    yfinance data provider (free, no API key required).

    Uses Yahoo Finance via the yfinance library.
    All calls are wrapped in asyncio.to_thread for async compatibility.
    """

    provider_name = "yfinance"

    def __init__(self, api_key: str = "") -> None:
        """
        Initialize yfinance provider.

        Note: yfinance doesn't require an API key. The api_key parameter
        is kept for interface compatibility.

        Args:
            api_key: Ignored (kept for protocol compatibility)
        """
        self._ticker_cache: dict[str, object] = {}

    def _get_ticker(self, symbol: str):
        """Get or create a yfinance Ticker object (cached)."""
        if symbol not in self._ticker_cache:
            import yfinance as yf

            self._ticker_cache[symbol] = yf.Ticker(symbol)
        return self._ticker_cache[symbol]

    def _run_sync(self, func, *args, **kwargs):
        """
        Run a synchronous function in a thread pool.

        Args:
            func: Synchronous function to run
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Function result
        """
        return asyncio.to_thread(func, *args, **kwargs)

    # ========================================================================
    # FundamentalsProvider Implementation
    # ========================================================================

    async def get_income_statement(
        self, ticker: str, period: str = "annual", limit: int = 5
    ) -> list[IncomeStatement]:
        """
        Get income statement data.

        Args:
            ticker: Stock symbol
            period: "annual" or "quarterly"
            limit: Number of periods to return

        Returns:
            List of IncomeStatement objects
        """
        ticker_obj = self._get_ticker(ticker)

        def _fetch():
            if period == "annual":
                df = ticker_obj.get_income_stmt(as_dict=False)
            else:
                df = ticker_obj.get_income_stmt(freq="quarterly", as_dict=False)
            return df

        df = await self._run_sync(_fetch)

        if df is None or df.empty:
            return []

        statements = []
        for col in df.columns[:limit]:
            period_date = col.to_pydatetime().date()
            period_type = PeriodType.ANNUAL if period == "annual" else PeriodType.QUARTERLY

            # Extract values (yfinance uses specific index names)
            def get_value(index_name: str) -> Optional[float]:
                try:
                    val = df.loc[index_name, col]
                    return float(val) if val is not None and not (isinstance(val, float) and val != val) else None
                except (KeyError, ValueError):
                    return None

            # Map yfinance fields to our canonical model
            # Note: yfinance field names vary, using common ones
            stmt = IncomeStatement(
                ticker=ticker,
                period_date=period_date,
                period_type=period_type,
                currency="USD",  # yfinance doesn't always specify, assume USD for US stocks
                revenue=get_value("Total Revenue"),
                cost_of_revenue=get_value("Cost Of Revenue"),
                gross_profit=get_value("Gross Profit"),
                research_and_development=get_value("Research And Development"),
                selling_general_admin=get_value("Selling General Administrative"),
                total_operating_expenses=get_value("Total Operating Expenses"),
                operating_income=get_value("Operating Income"),
                ebitda=get_value("Ebitda"),
                depreciation_amortization=get_value("Reconciled Depreciation"),
                interest_expense=get_value("Interest Expense"),
                income_before_tax=get_value("Income Before Tax"),
                income_tax_expense=get_value("Income Tax Expense"),
                net_income=get_value("Net Income"),
                eps=get_value("Basic EPS"),
                eps_diluted=get_value("Diluted EPS"),
                shares_outstanding=get_value("Basic Average Shares"),
                shares_diluted=get_value("Diluted Average Shares"),
                source="yfinance",
            )
            statements.append(stmt)

        return statements

    async def get_balance_sheet(
        self, ticker: str, period: str = "annual", limit: int = 5
    ) -> list[BalanceSheet]:
        """
        Get balance sheet data.

        Args:
            ticker: Stock symbol
            period: "annual" or "quarterly"
            limit: Number of periods to return

        Returns:
            List of BalanceSheet objects
        """
        ticker_obj = self._get_ticker(ticker)

        def _fetch():
            if period == "annual":
                df = ticker_obj.get_balance_sheet(as_dict=False)
            else:
                df = ticker_obj.get_balance_sheet(freq="quarterly", as_dict=False)
            return df

        df = await self._run_sync(_fetch)

        if df is None or df.empty:
            return []

        statements = []
        for col in df.columns[:limit]:
            period_date = col.to_pydatetime().date()
            period_type = PeriodType.ANNUAL if period == "annual" else PeriodType.QUARTERLY

            def get_value(index_name: str) -> Optional[float]:
                try:
                    val = df.loc[index_name, col]
                    return float(val) if val is not None and not (isinstance(val, float) and val != val) else None
                except (KeyError, ValueError):
                    return None

            stmt = BalanceSheet(
                ticker=ticker,
                period_date=period_date,
                period_type=period_type,
                currency="USD",
                cash_and_equivalents=get_value("Cash And Cash Equivalents"),
                short_term_investments=get_value("Short Term Investments"),
                accounts_receivable=get_value("Net Receivables"),
                inventory=get_value("Inventory"),
                total_current_assets=get_value("Current Assets"),
                property_plant_equipment=get_value("Property Plant Equipment"),
                goodwill=get_value("Good Will"),
                intangible_assets=get_value("Intangible Assets"),
                total_assets=get_value("Total Assets"),
                accounts_payable=get_value("Accounts Payable"),
                short_term_debt=get_value("Short Term Debt"),
                total_current_liabilities=get_value("Current Liabilities"),
                long_term_debt=get_value("Long Term Debt"),
                total_liabilities=get_value("Total Liab"),
                total_stockholders_equity=get_value("Total Stockholder Equity"),
                shares_outstanding=get_value("Common Stock Shares Outstanding"),
                source="yfinance",
            )
            statements.append(stmt)

        return statements

    async def get_cash_flow(
        self, ticker: str, period: str = "annual", limit: int = 5
    ) -> list[CashFlow]:
        """
        Get cash flow statement data.

        Args:
            ticker: Stock symbol
            period: "annual" or "quarterly"
            limit: Number of periods to return

        Returns:
            List of CashFlow objects
        """
        ticker_obj = self._get_ticker(ticker)

        def _fetch():
            if period == "annual":
                df = ticker_obj.get_cashflow(as_dict=False)
            else:
                df = ticker_obj.get_cashflow(freq="quarterly", as_dict=False)
            return df

        df = await self._run_sync(_fetch)

        if df is None or df.empty:
            return []

        statements = []
        for col in df.columns[:limit]:
            period_date = col.to_pydatetime().date()
            period_type = PeriodType.ANNUAL if period == "annual" else PeriodType.QUARTERLY

            def get_value(index_name: str) -> Optional[float]:
                try:
                    val = df.loc[index_name, col]
                    return float(val) if val is not None and not (isinstance(val, float) and val != val) else None
                except (KeyError, ValueError):
                    return None

            stmt = CashFlow(
                ticker=ticker,
                period_date=period_date,
                period_type=period_type,
                currency="USD",
                operating_cash_flow=get_value("Operating Cash Flow"),
                capital_expenditure=get_value("Capital Expenditure"),
                free_cash_flow=None,  # yfinance doesn't provide this directly, could calculate
                dividends_paid=get_value("Cash Dividends Paid"),
                share_repurchase=None,  # Often part of "Repurchase Of Stock"
                financing_cash_flow=get_value("Financing Cash Flow"),
                investing_cash_flow=get_value("Investing Cash Flow"),
                source="yfinance",
            )
            statements.append(stmt)

        return statements

    async def get_financial_ratios(self, ticker: str) -> FinancialRatios:
        """
        Get financial ratios and valuation metrics.

        Args:
            ticker: Stock symbol

        Returns:
            FinancialRatios object
        """
        ticker_obj = self._get_ticker(ticker)

        def _fetch_info():
            return ticker_obj.info

        info = await self._run_sync(_fetch_info)

        if not info:
            raise ProviderError("yfinance", f"No data available for {ticker}")

        # Map yfinance info fields to our canonical model
        return FinancialRatios(
            ticker=ticker,
            pe_ratio=info.get("trailingPE"),
            ev_to_ebitda=info.get("enterpriseToEbitda"),
            price_to_book=info.get("priceToBook"),
            price_to_sales=info.get("priceToSalesTrailing12Months"),
            return_on_equity=info.get("returnOnEquity"),
            return_on_assets=info.get("returnOnAssets"),
            return_on_invested_capital=info.get("returnOnCapital"),
            gross_margin=info.get("profitMargins", {}).get("gross") if isinstance(info.get("profitMargins"), dict) else info.get("grossMargins"),
            operating_margin=info.get("profitMargins", {}).get("operating") if isinstance(info.get("profitMargins"), dict) else info.get("operatingMargins"),
            net_margin=info.get("profitMargins", {}).get("net") if isinstance(info.get("profitMargins"), dict) else info.get("profitMargins"),
            debt_to_equity=None,  # yfinance has various debt metrics, need to calculate
            current_ratio=info.get("currentRatio"),
            fcf_yield=None,  # Need to calculate from FCF and market cap
            dividend_yield=info.get("dividendYield"),
            peg_ratio=info.get("pegRatio"),
            source="yfinance",
        )

    # ========================================================================
    # PriceProvider Implementation
    # ========================================================================

    async def get_quote(self, ticker: str) -> StockQuote:
        """
        Get real-time stock quote.

        Args:
            ticker: Stock symbol

        Returns:
            StockQuote with current price and change
        """
        ticker_obj = self._get_ticker(ticker)

        def _fetch():
            return ticker_obj.info

        info = await self._run_sync(_fetch)

        if not info or "regularMarketPrice" not in info:
            raise ProviderError("yfinance", f"No quote data for {ticker}")

        current_price = info["regularMarketPrice"]
        previous_close = info.get("previousClose")
        current_price_float = float(current_price) if current_price is not None else 0.0

        change = None
        change_percent = None
        if previous_close is not None and previous_close > 0:
            change = current_price_float - float(previous_close)
            change_percent = (change / float(previous_close)) * 100

        return StockQuote(
            ticker=ticker,
            price=current_price_float,
            change=change,
            change_percent=change_percent,
            volume=info.get("regularMarketVolume"),
            market_cap=info.get("marketCap"),
            high=info.get("regularMarketDayHigh"),
            low=info.get("regularMarketDayLow"),
            open=info.get("regularMarketOpen"),
            previous_close=previous_close,
            timestamp=datetime.fromtimestamp(info.get("regularMarketTime", 0)) if info.get("regularMarketTime") else datetime.utcnow(),
            source="yfinance",
        )

    async def get_historical_prices(
        self, ticker: str, start: date, end: date, interval: str = "1d"
    ) -> list[PriceBar]:
        """
        Get historical OHLCV price bars.

        Args:
            ticker: Stock symbol
            start: Start date
            end: End date
            interval: Bar width (1d, 1w, 1h, etc.)

        Returns:
            List of PriceBar objects
        """
        ticker_obj = self._get_ticker(ticker)

        # yfinance interval mapping
        interval_map = {
            "1d": "1d",
            "1w": "1wk",
            "1M": "1mo",
            "1h": "1h",
            "15m": "15m",
            "5m": "5m",
            "1m": "1m",
        }
        yf_interval = interval_map.get(interval, "1d")

        def _fetch():
            return ticker_obj.history(
                start=start.strftime("%Y-%m-%d"),
                end=end.strftime("%Y-%m-%d"),
                interval=yf_interval,
            )

        df = await self._run_sync(_fetch)

        if df is None or df.empty:
            return []

        price_bars = []
        for idx, row in df.iterrows():
            # Handle both DatetimeIndex and regular index
            if hasattr(idx, "date"):
                bar_date = idx.date()
            else:
                bar_date = idx

            price_bars.append(
                PriceBar(
                    ticker=ticker,
                    date=bar_date,
                    open=float(row["Open"]),
                    high=float(row["High"]),
                    low=float(row["Low"]),
                    close=float(row["Close"]),
                    volume=int(row["Volume"]),
                    adjusted_close=float(row.get("Close", 0)),  # yfinance doesn't always provide adj close
                    source="yfinance",
                )
            )

        return price_bars

    # ========================================================================
    # ProfileProvider Implementation
    # ========================================================================

    async def get_company_profile(self, ticker: str) -> CompanyProfile:
        """
        Get company profile information.

        Args:
            ticker: Stock symbol

        Returns:
            CompanyProfile with company details
        """
        ticker_obj = self._get_ticker(ticker)

        def _fetch():
            return ticker_obj.info

        info = await self._run_sync(_fetch)

        if not info:
            raise ProviderError("yfinance", f"No profile data for {ticker}")

        # Parse IPO date if present
        ipo_date = None
        if info.get("ipoDate"):
            try:
                ipo_date = datetime.strptime(info["ipoDate"], "%Y-%m-%d").date()
            except (ValueError, TypeError):
                pass

        return CompanyProfile(
            ticker=ticker,
            company_name=info.get("longName") or info.get("shortName", ""),
            exchange=info.get("exchange"),
            sector=info.get("sector"),
            industry=info.get("industry"),
            market_cap=info.get("marketCap"),
            description=info.get("longBusinessSummary"),
            website=info.get("website"),
            ceo=info.get("companyOfficers", [{}])[0].get("name") if info.get("companyOfficers") else None,
            country=info.get("country"),
            employees=info.get("fullTimeEmployees"),
            ipo_date=ipo_date,
            source="yfinance",
        )

    async def search_ticker(self, query: str) -> list[TickerSearchResult]:
        """
        Search for tickers by company name or symbol.

        Note: yfinance doesn't have a direct search API, so we use an HTTPS GET
        to the Yahoo Finance v1 search endpoint which returns JSON results.

        Args:
            query: Search query (company name or symbol)

        Returns:
            List of matching ticker results
        """
        import httpx

        results = []

        # Try Yahoo Finance search API first
        search_url = "https://query1.finance.yahoo.com/v1/finance/search"
        params = {"q": query, "quotes_count": 10, "country": "US"}

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(search_url, params=params)
                response.raise_for_status()
                data = response.json()

            quotes = data.get("quotes", [])

            for quote in quotes[:10]:
                # Filter for equity securities only
                quote_type = quote.get("quoteType", "")
                if quote_type != "EQUITY":
                    continue

                symbol = quote.get("symbol", "")
                if not symbol:
                    continue

                results.append(
                    TickerSearchResult(
                        ticker=symbol,
                        name=quote.get("shortname", quote.get("longname", "")),
                        exchange=quote.get("exchange"),
                        type="stock",
                    )
                )

            if results:
                return results

        except Exception as e:
            logger = get_logger(__name__)
            logger.debug(f"Yahoo Finance search failed for '{query}': {e}")

        # Fallback: if search API returned no results or failed, try direct ticker lookup
        # First try the query as-is (in case it's a ticker symbol)
        try:
            ticker_obj = self._get_ticker(query)

            def _fetch():
                return ticker_obj.info

            info = await self._run_sync(_fetch)

            if info and (info.get("longName") or info.get("shortName")):
                results.append(
                    TickerSearchResult(
                        ticker=query.upper(),
                        name=info.get("longName") or info.get("shortName", ""),
                        exchange=info.get("exchange"),
                        type="stock",
                    )
                )
                return results
        except Exception:
            pass

        # Additional fallback: try common ticker mappings for well-known companies
        # This handles cases like "walmart" -> "WMT", "microsoft" -> "MSFT", etc.
        common_tickers = {
            "walmart": "WMT",
            "target": "TGT",
            "costco": "COST",
            "amazon": "AMZN",
            "google": "GOOGL",
            "alphabet": "GOOGL",
            "microsoft": "MSFT",
            "apple": "AAPL",
            "tesla": "TSLA",
            "netflix": "NFLX",
            "meta": "META",
            "facebook": "META",
            "nvidia": "NVDA",
            "jpmorgan": "JPM",
            "chase": "JPM",
            "bank of america": "BAC",
            "wells fargo": "WFC",
            "goldman sachs": "GS",
            "morgan stanley": "MS",
            "visa": "V",
            "mastercard": "MA",
            "paypal": "PYPL",
            "intel": "INTC",
            "amd": "AMD",
            "qualcomm": "QCOM",
            "cisco": "CSCO",
            "oracle": "ORCL",
            "ibm": "IBM",
            "salesforce": "CRM",
            "adobe": "ADBE",
            "sap": "SAP",
            "accenture": "ACN",
            "boeing": "BA",
            "airbus": "AIR",
            "lockheed martin": "LMT",
            "general dynamics": "GD",
            "caterpillar": "CAT",
            "deere": "DE",
            "3m": "MMM",
            "honeywell": "HON",
            "unitedhealth": "UNH",
            "johnson & johnson": "JNJ",
            "johnson and johnson": "JNJ",
            "pfizer": "PFE",
            "merck": "MRK",
            "abbvie": "ABBV",
            "thermo fisher": "TMO",
            "danaher": "DHR",
            "roche": "RHHBY",
            "novartis": "NVS",
            "gilead": "GILD",
            "bristol-myers squibb": "BMY",
            "bristol myers squibb": "BMY",
            "exxonmobil": "XOM",
            "exxon mobil": "XOM",
            "chevron": "CVX",
            "conocophillips": "COP",
            "schlumberger": "SLB",
            "halliburton": "HAL",
            "baker hughes": "BKR",
            "occidental petroleum": "OXY",
            "devon energy": "DVN",
            "eoG resources": "EOG",
            "pegasus": "PXD",
            "coca-cola": "KO",
            "cocacola": "KO",
            "pepsi": "PEP",
            "pepsico": "PEP",
            "nestle": "NSRGY",
            "unilever": "UL",
            "procter & gamble": "PG",
            "procter and gamble": "PG",
            "colgate-palmolive": "CL",
            "kimberly-clark": "KMB",
            "mcdonald's": "MCD",
            "mcdonalds": "MCD",
            "starbucks": "SBUX",
            "nike": "NKE",
            "adidas": "ADDYY",
            "lululemon": "LULU",
            "under armour": "UAA",
            "gap": "GPS",
            "home depot": "HD",
            "lowe's": "LOW",
            "lowes": "LOW",
            "menards": "MRK",
            "best buy": "BBY",
            "gamestop": "GME",
            "amc": "AMC",
            "disney": "DIS",
            "warner bros": "WBD",
            "paramount": "PARA",
            "sony": "SONY",
            "comcast": "CMCSA",
            "verizon": "VZ",
            "at&t": "T",
            "at and t": "T",
            "t-mobile": "TMUS",
            "tmobile": "TMUS",
            "sprint": "S",
            "ford": "F",
            "general motors": "GM",
            "chevrolet": "GM",
            "cadillac": "GM",
            "gmc": "GM",
            "rivian": "RIVN",
            "lucid": "LCID",
            "nio": "NIO",
            "byd": "BYDDY",
            "toyota": "TM",
            "honda": "HMC",
            "nissan": "NSANY",
            "bmw": "BMWYY",
            "mercedes-benz": "MBGYY",
            "mercedes benz": "MBGYY",
            "volkswagen": "VWAGY",
            "porsche": "POAHY",
            "ferrari": "RACE",
            "uber": "UBER",
            "lyft": "LYFT",
            "doordash": "DASH",
            "airbnb": "ABNB",
            "booking holdings": "BKNG",
            "expedia": "EXPE",
            "tripadvisor": "TRIP",
            "marriott": "MAR",
            "hilton": "HLT",
            "hyatt": "H",
            "ihg": "IHG",
            "choice hotels": "CHH",
            "wyndham": "WH",
            "radisson": "RDH",
            "american airlines": "AAL",
            "delta": "DAL",
            "united airlines": "UAL",
            "southwest": "LUV",
            "jetblue": "JBLU",
            "alaska air": "ALK",
            "spirit airlines": "SAVE",
            "frontier": "FYBR",
            "carnival": "CCL",
            "royal caribbean": "RCL",
            "norwegian cruise line": "NCLH",
        }

        query_lower = query.lower().strip()
        if query_lower in common_tickers:
            ticker = common_tickers[query_lower]
            try:
                ticker_obj = self._get_ticker(ticker)

                def _fetch():
                    return ticker_obj.info

                info = await self._run_sync(_fetch)
                if info and (info.get("longName") or info.get("shortName")):
                    results.append(
                        TickerSearchResult(
                            ticker=ticker,
                            name=info.get("longName") or info.get("shortName", ""),
                            exchange=info.get("exchange"),
                            type="stock",
                        )
                    )
                    return results
            except Exception:
                # If ticker lookup fails, still return the ticker with the query as name
                results.append(
                    TickerSearchResult(
                        ticker=ticker,
                        name=query.title(),
                        exchange="NYSE" if ticker not in ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "NVDA", "META", "NFLX"] else "NASDAQ",
                        type="stock",
                    )
                )
                return results

        return results

    # ========================================================================
    # NewsProvider Implementation
    # ========================================================================

    async def get_news(self, ticker: str, limit: int = 20) -> list[NewsItem]:
        """
        Get recent news for a ticker from Yahoo Finance.

        Uses Yahoo Finance search API as primary source (more reliable than RSS).
        Falls back to RSS feed if search API fails.

        Args:
            ticker: Stock symbol
            limit: Maximum number of articles (default 20)

        Returns:
            List of NewsItem
        """
        logger = get_logger(__name__)

        # Try Yahoo Finance search API first (more reliable)
        news_url = "https://query1.finance.yahoo.com/v1/finance/search"
        params = {
            "q": ticker.upper(),
            "quotesCount": 1,
            "newsCount": limit,
            "country": "US",
        }

        try:
            async with httpx.AsyncClient(timeout=10.0, headers={"User-Agent": "Mozilla/5.0"}) as client:
                response = await client.get(news_url, params=params)
                response.raise_for_status()
                data = response.json()

            news_results = data.get("news", [])
            articles = []

            for item in news_results[:limit]:
                try:
                    headline = item.get("title", "")
                    link = item.get("link", "")
                    pub_date = item.get("providerPublishTime", 0)
                    publisher = item.get("publisher", "Yahoo Finance")
                    thumbnail = item.get("thumbnail", {})
                    content_resolution = thumbnail.get("resolutions", [{}])[-1] if thumbnail else {}

                    # Parse publication date (Unix timestamp)
                    if isinstance(pub_date, int) and pub_date > 0:
                        published_at = datetime.fromtimestamp(pub_date)
                    else:
                        published_at = datetime.utcnow()

                    # Summary may be in different fields
                    summary = item.get("summary") or item.get("content", {}).get("content") or ""

                    articles.append(
                        NewsItem(
                            headline=headline,
                            summary=summary[:500] if summary else None,
                            source_name=publisher,
                            source_url=link if link else None,
                            ticker=ticker.upper(),
                            published_at=published_at,
                            sentiment_score=None,
                            sentiment_label=None,
                            relevance_score=None,
                            source="yfinance",
                            fetched_at=datetime.utcnow(),
                        )
                    )
                except Exception as e:
                    logger.debug(f"Error parsing news item: {e}")
                    continue

            # Sort by date (most recent first)
            articles.sort(key=lambda x: x.published_at, reverse=True)

            logger.info(f"Fetched {len(articles)} news articles for {ticker} from Yahoo Finance API")
            return articles

        except httpx.HTTPError as e:
            logger.warning(f"Yahoo Finance API failed for {ticker}: {e}. Falling back to RSS...")
            # Fall back to RSS feed
            return await self._get_news_rss(ticker, limit)
        except Exception as e:
            logger.error(f"Unexpected error fetching news for {ticker}: {e}")
            # Fall back to RSS feed
            return await self._get_news_rss(ticker, limit)

    async def _get_news_rss(self, ticker: str, limit: int = 20) -> list[NewsItem]:
        """
        Fallback: Get news from Yahoo Finance RSS feed.

        Args:
            ticker: Stock symbol
            limit: Maximum number of articles

        Returns:
            List of NewsItem
        """
        logger = get_logger(__name__)
        rss_url = f"https://finance.yahoo.com/rss/symbol/{ticker.upper()}"

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(rss_url)
                response.raise_for_status()
                xml_content = response.text

            root = ET.fromstring(xml_content)
            namespaces = {
                'content': 'http://purl.org/rss/1.0/modules/content/',
                'dc': 'http://purl.org/dc/elements/1.1/',
            }

            articles = []
            for item in root.findall('.//item'):
                if len(articles) >= limit:
                    break

                try:
                    headline = item.findtext('title', '')
                    link = item.findtext('link', '')
                    pub_date_str = item.findtext('pubDate', '')
                    content_encoded = item.findtext('content:encoded', '', namespaces)
                    description = item.findtext('description', '')

                    published_at = datetime.utcnow()
                    if pub_date_str:
                        try:
                            published_at = datetime.strptime(
                                pub_date_str, "%a, %d %b %Y %H:%M:%S %Z"
                            )
                        except ValueError:
                            try:
                                published_at = datetime.strptime(
                                    pub_date_str, "%a, %d %b %Y %H:%M:%S GMT"
                                )
                            except ValueError:
                                pass

                    summary = self._strip_html_tags(content_encoded or description or "")

                    articles.append(
                        NewsItem(
                            headline=headline,
                            summary=summary[:500] if summary else None,
                            source_name="Yahoo Finance",
                            source_url=link if link else None,
                            ticker=ticker.upper(),
                            published_at=published_at,
                            sentiment_score=None,
                            sentiment_label=None,
                            relevance_score=None,
                            source="yfinance",
                            fetched_at=datetime.utcnow(),
                        )
                    )
                except Exception as e:
                    logger.debug(f"Error parsing RSS item: {e}")
                    continue

            articles.sort(key=lambda x: x.published_at, reverse=True)
            logger.info(f"Fetched {len(articles)} news articles for {ticker} from Yahoo Finance RSS")
            return articles

        except Exception as e:
            logger.warning(f"RSS fallback failed for {ticker}: {e}")
            return []

    def _strip_html_tags(self, text: str) -> str:
        """Strip HTML tags from text."""
        import re
        # Remove HTML tags
        clean = re.sub(r'<[^<]+?>', '', text)
        # Decode common HTML entities
        clean = clean.replace('&nbsp;', ' ')
        clean = clean.replace('&amp;', '&')
        clean = clean.replace('&lt;', '<')
        clean = clean.replace('&gt;', '>')
        clean = clean.replace('&quot;', '"')
        clean = clean.replace('&#39;', "'")
        # Remove extra whitespace
        clean = ' '.join(clean.split())
        return clean


# Self-registration
from app.services.data.registry import (
    register_fundamentals,
    register_prices,
    register_profiles,
    register_news,
)

register_fundamentals("yfinance", YFinanceProvider)
register_prices("yfinance", YFinanceProvider)
register_profiles("yfinance", YFinanceProvider)
register_news("yfinance", YFinanceProvider)
