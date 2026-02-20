from __future__ import annotations

from datetime import date
from unittest.mock import AsyncMock, Mock, patch

import httpx
import pytest

from app.core.errors import ProviderError
from app.services.data.providers.sec_edgar import SECEdgarProvider, SECFiling


class TestSECEdgarProvider:
    """Test suite for SEC EDGAR provider."""

    @pytest.fixture
    def provider(self):
        return SECEdgarProvider()

    @pytest.fixture
    def mock_http_client(self):
        return AsyncMock()

    async def test_get_cik_success(self, provider, mock_http_client):
        """Test CIK lookup success."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "0": {"cik_str": 320193, "ticker": "AAPL", "title": "Apple Inc."}
        }
        mock_response.raise_for_status = Mock()

        with patch.object(provider, "_get_client", return_value=mock_http_client):
            mock_http_client.get.return_value = mock_response

            cik = await provider._get_cik("AAPL")

            assert cik == "0000320193"

    async def test_get_cik_not_found(self, provider, mock_http_client):
        """Test CIK lookup not found."""
        mock_response = Mock()
        mock_response.json.return_value = {}
        mock_response.raise_for_status = Mock()

        with patch.object(provider, "_get_client", return_value=mock_http_client):
            mock_http_client.get.return_value = mock_response

            with pytest.raises(ProviderError) as exc_info:
                await provider._get_cik("AAPL")

            assert "not found" in str(exc_info.value)

    async def test_get_filing_list_success(self, provider):
        """Test filing list retrieval."""
        filings_response = {
            "recent": {
                "accessionNumber": ["0000320193-23-000077"],
                "filingDate": ["2023-11-03"],
                "form": ["10-K"],
                "primaryDocument": ["aapl-20230930.htm"],
                "primaryDocDescription": ["10-K"],
            }
        }

        with patch.object(provider, "_get_cik", new=AsyncMock(return_value="0000320193")):
            with patch.object(provider, "_request", new=AsyncMock(return_value=filings_response)):
                filings = await provider.get_filing_list("AAPL", filing_type="10-K")

                assert len(filings) == 1
                assert isinstance(filings[0], SECFiling)
                assert filings[0].ticker == "AAPL"
                assert filings[0].filing_type == "10-K"
                assert filings[0].filed_date == date(2023, 11, 3)
                assert "0000320193" in filings[0].primary_document

    async def test_get_filing_list_filter_type(self, provider):
        """Test filing type filtering."""
        filings_response = {
            "recent": {
                "accessionNumber": ["0000320193-23-000077", "0000320193-23-000064"],
                "filingDate": ["2023-11-03", "2023-08-04"],
                "form": ["10-K", "10-Q"],
                "primaryDocument": ["aapl-20230930.htm", "aapl-20230701.htm"],
                "primaryDocDescription": ["10-K", "10-Q"],
            }
        }

        with patch.object(provider, "_get_cik", new=AsyncMock(return_value="0000320193")):
            with patch.object(provider, "_request", new=AsyncMock(return_value=filings_response)):
                filings = await provider.get_filing_list("AAPL", filing_type="10-K")

                assert len(filings) == 1
                assert filings[0].filing_type == "10-K"
                assert filings[0].accession_number == "0000320193-23-000077"

    async def test_get_filing_text_success(self, provider, mock_http_client):
        """Test filing text retrieval."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "hits": {
                "hits": [
                    {
                        "_source": {
                            "file_description": "Form 10-K Annual Report"
                        }
                    }
                ]
            }
        }

        with patch.object(provider, "_get_client", return_value=mock_http_client):
            mock_http_client.get.return_value = mock_response

            text = await provider.get_filing_text("0000320193-23-000077")

            assert text == "Form 10-K Annual Report"

    async def test_get_filing_text_error(self, provider, mock_http_client):
        """Test filing text error handling."""
        with patch.object(provider, "_get_client", return_value=mock_http_client):
            mock_http_client.get.side_effect = httpx.HTTPError("Not found")

            with pytest.raises(ProviderError) as exc_info:
                await provider.get_filing_text("0000320193-23-000077")

            assert "Failed to fetch filing text" in str(exc_info.value)

    async def test_cik_cache(self, provider, mock_http_client):
        """Test CIK caching."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "0": {"cik_str": 320193, "ticker": "AAPL", "title": "Apple Inc."}
        }
        mock_response.raise_for_status = Mock()

        with patch.object(provider, "_get_client", return_value=mock_http_client):
            mock_http_client.get.return_value = mock_response

            cik_first = await provider._get_cik("AAPL")
            cik_second = await provider._get_cik("AAPL")

            assert cik_first == "0000320193"
            assert cik_second == "0000320193"
            assert mock_http_client.get.call_count == 1
