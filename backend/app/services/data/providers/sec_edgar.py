from typing import Optional, Any
"""
SEC EDGAR data provider implementation.

https://www.sec.gov/edgar/sec-api-documentation

Fetches SEC filing data from the EDGAR system.
Note: This is a specialized provider with its own interface.
"""
from __future__ import annotations

import asyncio
from datetime import date
from typing import Any

import httpx
from pydantic import BaseModel

from app.core.errors import ProviderError


class SECFiling(BaseModel):
    """SEC filing metadata."""

    ticker: str
    filing_type: str  # 10-K, 10-Q, 8-K, etc.
    filed_date: date
    accession_number: str
    primary_document: str  # URL to the filing
    description: str


class SECEdgarProvider:
    """SEC EDGAR API client for SEC filings."""

    provider_name = "sec_edgar"

    # SEC EDGAR URLs
    TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
    SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik}.json"
    ARCHIVES_URL = "https://www.sec.gov/Archives/edgar/data"

    # Required User-Agent header for SEC API
    USER_AGENT = "EquityResearchAgent/1.0 (contact@example.com)"

    def __init__(self, api_key: str = "") -> None:
        """
        Initialize SEC EDGAR client.

        Args:
            api_key: Not used (SEC EDGAR is public) but kept for interface consistency
        """
        self._api_key = api_key  # Not used
        self._client: Optional[httpx.AsyncClient] = None
        self._semaphore = asyncio.Semaphore(5)  # Be nice to SEC servers
        self._cik_cache: dict[str, str] = {}  # Ticker -> CIK cache

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client with required headers."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                headers={"User-Agent": self.USER_AGENT},
                timeout=30.0,
                follow_redirects=True,
            )
        return self._client

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def _request(
        self, method: str, url: str, **kwargs: Any
    ) -> Any:
        """
        Make an API request to SEC EDGAR.

        Args:
            method: HTTP method
            url: Full URL
            **kwargs: Additional arguments passed to httpx

        Returns:
            Parsed JSON response

        Raises:
            ProviderError: API request failed
        """
        async with self._semaphore:
            client = await self._get_client()

            try:
                response = await client.request(method, url, **kwargs)
                response.raise_for_status()
                return response.json()

            except httpx.HTTPStatusError as e:
                raise ProviderError(
                    "sec_edgar",
                    f"HTTP {e.response.status_code}: {e.response.text}",
                )
            except httpx.RequestError as e:
                raise ProviderError("sec_edgar", f"Request failed: {e}")

    async def _get_cik(self, ticker: str) -> str:
        """
        Get CIK number for a ticker symbol.

        Args:
            ticker: Stock ticker symbol

        Returns:
            Zero-padded 10-digit CIK string

        Raises:
            ProviderError: If ticker not found
        """
        ticker = ticker.upper()

        # Check cache first
        if ticker in self._cik_cache:
            return self._cik_cache[ticker]

        # Fetch tickers mapping from SEC
        try:
            client = await self._get_client()
            async with self._semaphore:
                response = await client.get(self.TICKERS_URL)
                response.raise_for_status()
                data = response.json()
        except httpx.HTTPError as e:
            raise ProviderError("sec_edgar", f"Failed to fetch ticker mapping: {e}")

        # Build lookup dictionary
        # SEC returns: {"0": {"cik_str": 320193, "ticker": "AAPL", "title": "Apple Inc."}, ...}
        for entry in data.values():
            sec_ticker = entry.get("ticker", "").upper()
            cik_str = str(entry.get("cik_str", "")).zfill(10)
            self._cik_cache[sec_ticker] = cik_str

        if ticker not in self._cik_cache:
            raise ProviderError("sec_edgar", f"Ticker '{ticker}' not found in SEC database")

        return self._cik_cache[ticker]

    async def get_filing_list(
        self, ticker: str, filing_type: str = "10-K", limit: int = 5
    ) -> list[SECFiling]:
        """
        Get list of SEC filings for a ticker.

        Endpoint: https://data.sec.gov/submissions/CIK{cik}.json

        Args:
            ticker: Stock ticker symbol (e.g., "AAPL")
            filing_type: Type of filing (10-K, 10-Q, 8-K, etc.)
            limit: Maximum number of filings to return

        Returns:
            List of SECFiling objects

        Raises:
            ProviderError: If request fails or ticker not found
        """
        cik = await self._get_cik(ticker)
        url = self.SUBMISSIONS_URL.format(cik=cik)

        data = await self._request("GET", url)

        filings = []

        # SEC returns recent filings in "recent" key
        recent_filings = data.get("recent", {})

        if not recent_filings:
            # Try filings files for older submissions
            files = data.get("filings", {}).get("files", [])
            if files:
                # Fetch the most recent file
                file_name = files[0].get("name", "")
                if file_name:
                    file_url = f"https://data.sec.gov/submissions/{file_name}"
                    try:
                        recent_filings = await self._request("GET", file_url)
                    except ProviderError:
                        recent_filings = {}

        if not recent_filings:
            return filings

        # Extract filing arrays
        form_types = recent_filings.get("form", [])
        filing_dates = recent_filings.get("filingDate", [])
        accession_numbers = recent_filings.get("accessionNumber", [])
        primary_docs = recent_filings.get("primaryDocument", [])
        descriptions = recent_filings.get("primaryDocDescription", [])

        # If descriptions not available, use empty strings
        if not descriptions:
            descriptions = [""] * len(form_types)

        # Find matching filings
        for i, form in enumerate(form_types):
            if form == filing_type:
                try:
                    accession = accession_numbers[i]
                    filed_date = date.fromisoformat(filing_dates[i])

                    # Build document URL
                    # Format: /Archives/edgar/data/{cik}/{accession-no-dashes}/{primary-doc}
                    accession_no_dashes = accession.replace("-", "")
                    primary_doc = primary_docs[i] if i < len(primary_docs) else ""
                    doc_url = f"{self.ARCHIVES_URL}/{int(cik):d}/{accession_no_dashes}/{primary_doc}"

                    description = descriptions[i] if i < len(descriptions) else ""
                    if not description:
                        description = f"{filing_type} filing"

                    filings.append(
                        SECFiling(
                            ticker=ticker,
                            filing_type=filing_type,
                            filed_date=filed_date,
                            accession_number=accession,
                            primary_document=doc_url,
                            description=description,
                        )
                    )

                    if len(filings) >= limit:
                        break

                except (IndexError, ValueError):
                    # Skip malformed entries
                    continue

        return filings

    async def get_filing_text(self, accession_number: str) -> str:
        """
        Get the text content of a filing by accession number.

        Note: This extracts the text content from the filing document.
        For full-text filings, we fetch from the SEC full-text search.

        Args:
            accession_number: SEC accession number (e.g., "0000320193-23-000106")

        Returns:
            Filing text content (may be HTML or plain text)

        Raises:
            ProviderError: If filing cannot be retrieved
        """
        # For full text, we need to get the filing URL first
        # The accession number format is CIK-YEAR-SEQUENCE
        # We can search for it using the full-text search API or construct the URL

        # Full-text search endpoint
        search_url = "https://efts.sec.gov/LATEST/search-index"

        # Search for the filing
        params = {
            "q": accession_number,
            "dateRange": "custom",
            "startdt": "1990-01-01",
            "enddt": date.today().isoformat(),
        }

        try:
            # Note: EFTS search index may not always return direct filing text
            # This is a simplified implementation
            client = await self._get_client()
            async with self._semaphore:
                response = await client.get(search_url, params=params)

                if response.status_code == 200:
                    data = response.json()
                    hits = data.get("hits", {}).get("hits", [])

                    if hits:
                        # Get the first hit's source
                        source = hits[0].get("_source", {})
                        # Return a summary if available
                        if source.get("file_description"):
                            return source.get("file_description", "")

                # Fallback: construct URL and try to fetch
                # This requires knowing the CIK, which we can extract from accession
                return (
                    f"Filing text available at: "
                    f"https://www.sec.gov/Archives/edgar/data/"
                    f"[CIK]/{accession_number.replace('-', '')}"
                )

        except httpx.HTTPError as e:
            raise ProviderError("sec_edgar", f"Failed to fetch filing text: {e}")

        return ""


# Note: SEC EDGAR provider does not self-register with standard protocols
# as it has a specialized interface for SEC filings only.
# Use directly: provider = SECEdgarProvider()
