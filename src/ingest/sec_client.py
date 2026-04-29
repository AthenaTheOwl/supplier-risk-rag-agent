"""Small SEC EDGAR client with rate limiting and local raw cache."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from src.config import sec_user_agent

SEC_DATA_BASE = "https://data.sec.gov"
SEC_ARCHIVES_BASE = "https://www.sec.gov/Archives/edgar/data"


class SECClientError(RuntimeError):
    """Raised for EDGAR request failures with remediation hints."""


@dataclass
class RateLimiter:
    requests_per_second: float = 9.5

    def __post_init__(self) -> None:
        self._lock = asyncio.Lock()
        self._last_request = 0.0

    async def wait(self) -> None:
        async with self._lock:
            now = asyncio.get_running_loop().time()
            interval = 1.0 / self.requests_per_second
            delay = max(0.0, self._last_request + interval - now)
            if delay:
                await asyncio.sleep(delay)
            self._last_request = asyncio.get_running_loop().time()


class SECClient:
    def __init__(
        self,
        *,
        user_agent: str | None = None,
        raw_cache: str | Path = "data/raw",
        requests_per_second: float = 9.5,
    ) -> None:
        self.user_agent = user_agent or sec_user_agent()
        self.raw_cache = Path(raw_cache)
        self.rate_limiter = RateLimiter(requests_per_second=requests_per_second)
        self.headers = {"User-Agent": self.user_agent, "Accept-Encoding": "gzip, deflate"}

    @retry(
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.TransportError)),
        wait=wait_exponential(multiplier=0.5, min=0.5, max=8),
        stop=stop_after_attempt(4),
        reraise=True,
    )
    async def _get(self, url: str) -> httpx.Response:
        await self.rate_limiter.wait()
        async with httpx.AsyncClient(
            headers=self.headers,
            timeout=30.0,
            follow_redirects=True,
        ) as client:
            response = await client.get(url)
        if response.status_code == 403:
            raise SECClientError(
                "SEC returned 403. Set SEC_USER_AGENT to a descriptive app name and email."
            )
        if response.status_code == 429:
            raise SECClientError("SEC returned 429. Reduce request rate and retry later.")
        if response.status_code >= 400:
            raise SECClientError(f"SEC request failed with HTTP {response.status_code}: {url}")
        return response

    async def fetch_company_submissions(self, cik: str) -> dict[str, Any]:
        normalized = cik.zfill(10)
        url = f"{SEC_DATA_BASE}/submissions/CIK{normalized}.json"
        response = await self._get(url)
        return response.json()

    async def fetch_filing_html(self, cik: str, accession: str, primary_doc: str) -> str:
        normalized_cik = str(int(cik))
        accession_no_dash = accession.replace("-", "")
        cache_path = self.raw_cache / cik.zfill(10) / f"{accession}.html"
        if cache_path.exists():
            return cache_path.read_text(encoding="utf-8")
        url = f"{SEC_ARCHIVES_BASE}/{normalized_cik}/{accession_no_dash}/{primary_doc}"
        response = await self._get(url)
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(response.text, encoding="utf-8")
        return response.text
