"""
Lead generation service: search the web, filter with AI, and extract contact data.
This mirrors the existing lead-gen script's OpenAI usage to avoid extra credits.
"""
from __future__ import annotations

import logging
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Iterable, List, Optional, Sequence, Tuple
from urllib.parse import urljoin, urlparse, parse_qs, unquote

import requests
from bs4 import BeautifulSoup
try:
    from ddgs import DDGS
except ImportError:  # pragma: no cover - fallback for older package name
    from duckduckgo_search import DDGS
from openai import OpenAI

from app.config import safety_config
from app.services.lead_service import LeadService

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SearchLead:
    name: str
    website: Optional[str]
    snippet: Optional[str]
    source: str
    confidence: float


EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
NAME_RE = re.compile(r"\b([A-Z][a-z]+)\s+([A-Z][a-z]+)\b")
ROLE_RE = re.compile(
    r"\b("
    r"CEO|Chief\s+Executive\s+Officer|Chief\s+Marketing\s+Officer|Chief\s+Operating\s+Officer|"
    r"Founder|Co[- ]Founder|Owner|Co[- ]Owner|Director|Managing\s+Director|Manager|"
    r"VP|Vice\s+President|President|Head|Lead|Partner|Principal|Officer|"
    r"Marketing|Sales|Operations|Business\s+Development|Growth|Talent|HR|Human\s+Resources|"
    r"Creative\s+Director|Account\s+Director|Strategy|Strategist"
    r")"
    r"(?:\s+(?:of|,)\s+[A-Za-z& ]{2,40})?",
    re.IGNORECASE,
)

NAME_STOPWORDS = {
    "Contact",
    "Team",
    "Support",
    "Sales",
    "Info",
    "Email",
    "Office",
    "Service",
    "Careers",
    "Jobs",
    "Do",
    "No",
    "Not",
    "Our",
    "We",
    "Us",
    "The",
    "And",
}

GENERIC_EMAIL_LOCAL = {
    "info",
    "support",
    "sales",
    "contact",
    "hello",
    "team",
    "enquiry",
    "inquiry",
    "admin",
    "office",
    "marketing",
    "careers",
    "jobs",
    "hr",
    "billing",
    "accounts",
    "help",
    "service",
    "services",
    "press",
    "media",
    "partners",
}

LIST_PAGE_PATTERNS = [
    re.compile(r"\btop\s+\d+\b", re.IGNORECASE),
    re.compile(r"\bbest\s+\d+\b", re.IGNORECASE),
    re.compile(r"\b(top|best)\s+(marketing|digital|creative|advertising|seo|branding)\b", re.IGNORECASE),
    re.compile(r"\bdirectory\b", re.IGNORECASE),
    re.compile(r"\blist\b", re.IGNORECASE),
    re.compile(r"\brankings?\b", re.IGNORECASE),
    re.compile(r"\breviews?\b", re.IGNORECASE),
    re.compile(r"\bcompare\b", re.IGNORECASE),
]

LIST_PAGE_DOMAINS = {
    "clutch.co",
    "upcity.com",
    "sortlist.com",
    "designrush.com",
    "agencyspotter.com",
    "themanifest.com",
    "goodfirms.co",
}

CONTENT_DOMAINS = {
    "forbes.com",
    "wikipedia.org",
    "medium.com",
    "blogspot.com",
    "wordpress.com",
    "substack.com",
    "quora.com",
    "reddit.com",
    "wikihow.com",
}

CONTENT_PAGE_PATTERNS = [
    re.compile(r"/blog(/|$)", re.IGNORECASE),
    re.compile(r"/blogs?/", re.IGNORECASE),
    re.compile(r"/insights?/", re.IGNORECASE),
    re.compile(r"/news/", re.IGNORECASE),
    re.compile(r"/resources?/", re.IGNORECASE),
    re.compile(r"/articles?/", re.IGNORECASE),
    re.compile(r"/story/", re.IGNORECASE),
    re.compile(r"/stories/", re.IGNORECASE),
    re.compile(r"/press/", re.IGNORECASE),
    re.compile(r"/podcast/", re.IGNORECASE),
    re.compile(r"/wiki/", re.IGNORECASE),
    re.compile(r"/glossary/", re.IGNORECASE),
    re.compile(r"\bwhat[-\s]?is\b", re.IGNORECASE),
    re.compile(r"\bdefinition\b", re.IGNORECASE),
    re.compile(r"\bguide\b", re.IGNORECASE),
    re.compile(r"\bexplained\b", re.IGNORECASE),
    re.compile(r"\bbest practices\b", re.IGNORECASE),
    re.compile(r"\bhow to\b", re.IGNORECASE),
]

AGENCY_KEYWORDS = [
    "marketing",
    "agency",
    "advertising",
    "branding",
    "creative",
    "digital",
    "company",
    "business",
    "services",
    "team",
    "contact",
    "seo",
    "social",
    "performance",
    "growth",
]

DEFAULT_LOCATION_EXPANSIONS = [
    "new york",
    "los angeles",
    "san francisco",
    "chicago",
    "toronto",
    "vancouver",
    "mexico city",
    "sao paulo",
    "buenos aires",
    "london",
    "manchester",
    "paris",
    "berlin",
    "madrid",
    "barcelona",
    "rome",
    "amsterdam",
    "stockholm",
    "zurich",
    "dublin",
    "dubai",
    "riyadh",
    "singapore",
    "hong kong",
    "tokyo",
    "seoul",
    "mumbai",
    "delhi",
    "sydney",
    "melbourne",
]


class LeadGenService:
    MIN_TARGET_LEADS = 10
    MAX_TARGET_LEADS = 20
    MAX_INITIAL_LEADS = 60
    TARGET_FINAL_LEADS = 20
    GOOGLE_CSE_MAX_RESULTS = 40
    MAX_QUERY_VARIANTS = 5
    MAX_COMPANIES_TO_CRAWL = 60
    MAX_PAGES_PER_COMPANY = 4
    MAX_LEADS_PER_COMPANY = 3
    SEARCH_TIMEOUT_SECONDS = 6
    CRAWL_TIMEOUT_SECONDS = 5
    TOTAL_TIME_BUDGET_SECONDS = int(os.getenv("LEADGEN_TOTAL_TIMEOUT_SECONDS", "45"))
    EXTRA_PATHS = [
        "/about-us",
        "/company",
        "/our-team",
        "/people",
        "/leadership",
        "/staff",
        "/team",
        "/who-we-are",
        "/contact-us",
    ]

    @staticmethod
    def search_and_extract(
        query: str,
        location: Optional[str],
        exclude_emails: Optional[Sequence[str]] = None,
        max_results: Optional[int] = None,
        target_leads: Optional[int] = None,
        use_ai_filter: Optional[bool] = None,
    ) -> List[dict]:
        leads, _ = LeadGenService.search_with_companies(
            query=query,
            location=location,
            exclude_emails=exclude_emails,
            max_results=max_results,
            target_leads=target_leads,
            use_ai_filter=use_ai_filter,
        )
        return leads

    @staticmethod
    def search_with_companies(
        query: str,
        location: Optional[str],
        exclude_emails: Optional[Sequence[str]] = None,
        max_results: Optional[int] = None,
        target_leads: Optional[int] = None,
        use_ai_filter: Optional[bool] = None,
    ) -> Tuple[List[dict], List[dict]]:
        """
        Search for businesses, filter list pages via OpenAI, and extract contacts.
        The max_results and target_leads are capped to preserve OpenAI usage.
        """
        target_leads = target_leads or LeadGenService.TARGET_FINAL_LEADS
        target_leads = max(
            LeadGenService.MIN_TARGET_LEADS,
            min(int(target_leads), LeadGenService.MAX_TARGET_LEADS),
        )
        max_results = min(
            max_results or max(target_leads * 3, LeadGenService.MAX_INITIAL_LEADS),
            120,
        )
        if use_ai_filter is None:
            use_ai_filter = os.getenv("LEADGEN_USE_AI_FILTER", "").strip() == "1"

        base_query = query.strip()
        queries = LeadGenService._expand_queries(base_query)
        if location:
            location_query = f"{base_query} {location}".strip()
            location_variants = LeadGenService._expand_queries(location_query)
            queries = location_variants + [q for q in queries if q not in location_variants]
        else:
            location_queries = [
                f"{base_query} {loc}".strip()
                for loc in DEFAULT_LOCATION_EXPANSIONS[:3]
            ]
            queries = [q for q in location_queries if q] + [q for q in queries if q not in location_queries]
        queries = queries[:LeadGenService.MAX_QUERY_VARIANTS]

        exclude_set = {e.lower().strip() for e in (exclude_emails or []) if e}
        candidates: List[dict] = []
        companies: List[dict] = []
        seen_companies = set()
        deadline = time.time() + LeadGenService.TOTAL_TIME_BUDGET_SECONDS

        company_goal = min(max(target_leads * 3, 30), LeadGenService.MAX_COMPANIES_TO_CRAWL)

        for idx, q in enumerate(queries):
            if len(companies) >= company_goal or time.time() >= deadline:
                break
            leads = LeadGenService._combined_search(
                q,
                max_results=max_results,
                use_google=idx == 0,
            )
            if not leads:
                continue
            filtered = leads
            if use_ai_filter:
                filtered = LeadGenService._select_actual_businesses(
                    leads=leads,
                    query_type=query,
                    target_leads=min(len(leads), target_leads),
                )
            for lead in filtered:
                company = LeadGenService._company_candidate_from_search(lead)
                if not company:
                    continue
                key = LeadGenService._company_key(company.get("website"))
                if not key or key in seen_companies:
                    continue
                seen_companies.add(key)
                companies.append(company)
            if len(companies) >= company_goal:
                break

        if companies:
            candidates = LeadGenService._enrich_companies_to_target(
                companies=companies,
                exclude_set=exclude_set,
                target_leads=target_leads,
                deadline=deadline,
            )

        return candidates, companies

    @staticmethod
    def _combined_search(query: str, max_results: int, use_google: bool = True) -> List[SearchLead]:
        return LeadGenService._discover_search_results(
            query,
            max_results=max_results,
            use_google=use_google,
        )

    @staticmethod
    def _discover_search_results(
        query: str,
        max_results: int,
        use_google: bool,
    ) -> List[SearchLead]:
        leads: List[SearchLead] = []
        remaining = max_results
        if use_google:
            cse_limit = min(remaining, LeadGenService.GOOGLE_CSE_MAX_RESULTS)
            leads.extend(LeadGenService._google_cse_search(query, max_results=cse_limit))
            remaining = max_results - len(leads)

        if remaining > 0:
            ddg_limit = min(remaining, max(20, remaining))
            leads.extend(LeadGenService._duckduckgo_html_search(query, max_results=ddg_limit))
            remaining = max_results - len(leads)
        if remaining > 0 and os.getenv("LEADGEN_ENABLE_BING", "").strip() == "1":
            leads.extend(
                LeadGenService._bing_search(
                    query,
                    max_results=remaining,
                )
            )
        if not leads:
            leads = LeadGenService._duckduckgo_search(query, max_results=max_results)
        leads = LeadGenService._dedupe_search_leads(leads)
        return LeadGenService._filter_list_pages(leads)

    @staticmethod
    def _google_cse_search(query: str, max_results: int) -> List[SearchLead]:
        if max_results <= 0:
            return []
        api_key = os.getenv("GOOGLE_CSE_API_KEY", "").strip()
        cx = os.getenv("GOOGLE_CSE_CX", "").strip()
        if not api_key or not cx:
            return []

        leads: List[SearchLead] = []
        keywords = AGENCY_KEYWORDS
        page_size = 10
        max_results = min(max_results, 100)
        max_pages = max(1, (max_results + page_size - 1) // page_size)
        session = requests.Session()
        gl = os.getenv("GOOGLE_CSE_GL", "").strip()
        hl = os.getenv("GOOGLE_CSE_HL", "").strip()

        for page in range(max_pages):
            start = page * page_size + 1
            if start > 91:
                break
            try:
                params = {
                    "key": api_key,
                    "cx": cx,
                    "q": query,
                    "start": start,
                    "num": page_size,
                }
                if gl:
                    params["gl"] = gl
                if hl:
                    params["hl"] = hl
                resp = session.get(
                    "https://www.googleapis.com/customsearch/v1",
                    params=params,
                    timeout=LeadGenService.SEARCH_TIMEOUT_SECONDS,
                )
                resp.raise_for_status()
                payload = resp.json()
            except Exception as exc:
                logger.warning("Google CSE search error: %s", exc)
                break

            items = payload.get("items") or []
            if not items:
                break

            for item in items:
                if len(leads) >= max_results:
                    break
                name = item.get("title", "")
                link = LeadGenService._clean_search_url(item.get("link", ""))
                snippet = item.get("snippet", "")
                if not name or not link or not link.startswith("http"):
                    continue
                confidence = 0.65
                if snippet and any(k in snippet.lower() for k in keywords):
                    confidence = 0.8
                leads.append(
                    SearchLead(
                        name=name,
                        website=link,
                        snippet=snippet,
                        source="google_cse",
                        confidence=confidence,
                    )
                )

            if len(leads) >= max_results or len(items) < 5:
                break
            time.sleep(0.2)

        return leads

    @staticmethod
    def _dedupe_search_leads(leads: Sequence[SearchLead]) -> List[SearchLead]:
        unique: List[SearchLead] = []
        seen = set()
        for lead in leads:
            url = lead.website or ""
            key = LeadGenService._search_lead_key(url)
            if not key or key in seen:
                continue
            seen.add(key)
            unique.append(lead)
        return unique

    @staticmethod
    def _search_lead_key(url: str) -> Optional[str]:
        cleaned = LeadGenService._clean_search_url(url)
        if not cleaned:
            return None
        parsed = urlparse(cleaned)
        if not parsed.netloc:
            return None
        path = parsed.path.rstrip("/")
        return f"{parsed.scheme}://{parsed.netloc}{path}".lower()

    @staticmethod
    def _clean_search_url(url: str) -> Optional[str]:
        if not url:
            return None
        if url.startswith("/"):
            url = urljoin("https://duckduckgo.com", url)
        parsed = urlparse(url)
        if parsed.netloc.endswith("duckduckgo.com") and parsed.path.startswith("/l/"):
            params = parse_qs(parsed.query)
            redirect = params.get("uddg", [None])[0]
            if redirect:
                return unquote(redirect)
        return url

    @staticmethod
    def _duckduckgo_search(query: str, max_results: int) -> List[SearchLead]:
        if max_results <= 0:
            return []
        try:
            ddgs = DDGS()
            results = ddgs.text(query, max_results=max_results)
        except Exception as exc:
            logger.warning("DuckDuckGo search error: %s", exc)
            return []

        leads: List[SearchLead] = []
        keywords = AGENCY_KEYWORDS

        for result in results:
            name = (result or {}).get("title", "")
            url = LeadGenService._clean_search_url((result or {}).get("href", ""))
            snippet = (result or {}).get("body", "")
            if not name or not url or not url.startswith("http"):
                continue
            confidence = 0.65
            if snippet and any(k in snippet.lower() for k in keywords):
                confidence = 0.8
            leads.append(
                SearchLead(
                    name=name,
                    website=url,
                    snippet=snippet,
                    source="duckduckgo",
                    confidence=confidence,
                )
            )

        return leads

    @staticmethod
    def _duckduckgo_html_search(query: str, max_results: int) -> List[SearchLead]:
        if max_results <= 0:
            return []
        url = "https://duckduckgo.com/html/"
        session = requests.Session()
        session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept-Language": "en-US,en;q=0.9",
            }
        )
        leads: List[SearchLead] = []
        keywords = AGENCY_KEYWORDS
        page_size = 30
        max_pages = max(1, (max_results + page_size - 1) // page_size)

        for page in range(max_pages):
            offset = page * page_size
            try:
                resp = session.get(
                    url,
                    params={"q": query, "s": offset},
                    timeout=LeadGenService.SEARCH_TIMEOUT_SECONDS,
                )
                resp.raise_for_status()
            except Exception as exc:
                logger.warning("DuckDuckGo HTML search error: %s", exc)
                break

            soup = BeautifulSoup(resp.text, "html.parser")
            items = soup.select(".results .result")
            if not items:
                break

            for it in items:
                if len(leads) >= max_results:
                    break
                link = it.select_one("a.result__a")
                snippet_tag = it.select_one(".result__snippet")
                if not link:
                    continue
                name = link.get_text(strip=True)
                href = LeadGenService._clean_search_url(link.get("href") or "")
                snippet = snippet_tag.get_text(strip=True) if snippet_tag else None
                if not name or not href or not href.startswith("http"):
                    continue
                confidence = 0.65
                if snippet and any(k in snippet.lower() for k in keywords):
                    confidence = 0.8

                leads.append(
                    SearchLead(
                        name=name,
                        website=href,
                        snippet=snippet,
                        source="duckduckgo_html",
                        confidence=confidence,
                    )
                )

            if len(leads) >= max_results or len(items) < 5:
                break
            time.sleep(0.3)

        return leads

    @staticmethod
    def _bing_search(query: str, max_results: int) -> List[SearchLead]:
        if max_results <= 0:
            return []
        url = "https://www.bing.com/search"
        session = requests.Session()
        session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/121.0 Safari/537.36"
                ),
                "Accept-Language": "en-US,en;q=0.9",
                "Referer": "https://www.bing.com/",
            }
        )
        leads: List[SearchLead] = []
        keywords = AGENCY_KEYWORDS
        page_size = 10
        max_pages = max(1, (max_results + page_size - 1) // page_size)

        for page in range(max_pages):
            first = page * page_size + 1
            try:
                resp = session.get(
                    url,
                    params={"q": query, "first": first, "count": page_size},
                    timeout=LeadGenService.SEARCH_TIMEOUT_SECONDS,
                )
                resp.raise_for_status()
            except Exception as exc:
                logger.warning("Bing request error: %s", exc)
                break

            soup = BeautifulSoup(resp.text, "html.parser")
            items = soup.select("li.b_algo")
            if not items:
                if page == 0:
                    logger.warning("No search results parsed from Bing.")
                break

            for it in items:
                if len(leads) >= max_results:
                    break
                link = it.select_one("h2 a")
                snippet_tag = it.select_one(".b_caption p, .b_snippet")
                if not link:
                    continue
                name = link.get_text(strip=True)
                href = LeadGenService._clean_search_url(link.get("href") or "")
                snippet = snippet_tag.get_text(strip=True) if snippet_tag else None
                if not name or not href or not href.startswith("http"):
                    continue

                confidence = 0.65
                if snippet and any(k in snippet.lower() for k in keywords):
                    confidence = 0.8

                leads.append(
                    SearchLead(
                        name=name,
                        website=href,
                        snippet=snippet,
                        source="bing",
                        confidence=confidence,
                    )
                )

            if len(leads) >= max_results or len(items) < 5:
                break
            time.sleep(0.3)

        return leads

    @staticmethod
    def _select_actual_businesses(
        leads: Iterable[SearchLead],
        query_type: str,
        target_leads: int,
    ) -> List[SearchLead]:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            logger.info("No OPENAI_API_KEY found. Skipping AI filtering.")
            return list(leads)[:target_leads]

        client = OpenAI(api_key=api_key)
        filtered: List[SearchLead] = []

        for lead in leads:
            if len(filtered) >= target_leads:
                break
            try:
                prompt = (
                    "Given this search result, determine if it's an actual "
                    f"{query_type} business/venue page or a list/directory page.\n\n"
                    f"Title: {lead.name}\n"
                    f"URL: {lead.website}\n"
                    f"Snippet: {lead.snippet}\n\n"
                    'Respond with ONLY one word: "ACTUAL" if it\'s an actual '
                    'individual business/venue page, or "LIST" if it\'s a '
                    'list/directory/aggregate page (like "Top 10", "Best of", '
                    "directories, etc)."
                )

                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0,
                    max_tokens=5,
                )
                result = response.choices[0].message.content.strip().upper()
                if "ACTUAL" in result:
                    filtered.append(lead)
            except Exception as exc:
                logger.warning("Error filtering %s: %s", lead.name, exc)
                filtered.append(lead)

            time.sleep(0.2)

        return filtered

    @staticmethod
    def _extract_contacts_from_lead(
        lead: SearchLead,
        max_candidates: int = 0,
    ) -> Tuple[List[dict], List[dict]]:
        if not lead.website:
            return [], []

        base_url = LeadGenService._normalize_base_url(lead.website)
        if not base_url:
            return [], []

        company_name = LeadGenService._derive_company_name(lead.name, base_url)
        strict_candidates: List[dict] = []
        partial_candidates: List[dict] = []
        seen_emails = set()

        paths = list(dict.fromkeys(safety_config.ALLOWED_PATHS + LeadGenService.EXTRA_PATHS))
        max_pages = min(
            safety_config.MAX_PAGES_PER_DOMAIN + 1,
            LeadGenService.MAX_PAGES_PER_COMPANY,
        )
        paths = paths[:max_pages]

        page_results: List[Tuple[List[dict], List[dict]]] = []
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = {
                executor.submit(
                    LeadGenService._extract_contacts_from_page,
                    urljoin(base_url, path),
                    company_name,
                    base_url,
                ): path
                for path in paths
            }
            for future in as_completed(futures):
                try:
                    result = future.result()
                except Exception as exc:
                    logger.debug("Contact extraction future failed for %s: %s", lead.website, exc)
                    continue
                if result:
                    page_results.append(result)

        for page_strict, page_partial in page_results:
            for bucket, target in ((page_strict, strict_candidates), (page_partial, partial_candidates)):
                for candidate in bucket:
                    email_lower = candidate["email"].lower().strip()
                    if email_lower in seen_emails:
                        continue
                    seen_emails.add(email_lower)
                    target.append(candidate)
                    if max_candidates > 0 and len(strict_candidates) + len(partial_candidates) >= max_candidates:
                        return strict_candidates, partial_candidates

        return strict_candidates, partial_candidates

    @staticmethod
    def _company_candidate_from_search(lead: SearchLead) -> Optional[dict]:
        if not lead.website:
            return None
        base_url = LeadGenService._normalize_base_url(lead.website)
        if not base_url:
            return None
        company_name = LeadGenService._derive_company_name(lead.name, base_url)
        if not company_name:
            return None
        return {
            "company": company_name,
            "website": base_url,
            "source_url": lead.website,
        }

    @staticmethod
    def _company_key(website: Optional[str]) -> Optional[str]:
        if not website:
            return None
        base_url = LeadGenService._normalize_base_url(website)
        if not base_url:
            return None
        return base_url.lower()

    @staticmethod
    def _enrich_companies_to_target(
        companies: Sequence[dict],
        exclude_set: set,
        target_leads: int,
        deadline: Optional[float] = None,
    ) -> List[dict]:
        if not companies or target_leads <= 0:
            return []
        leads: List[dict] = []
        seen_emails = set()
        max_workers = 4

        for idx in range(0, len(companies), max_workers):
            if deadline is not None and time.time() >= deadline:
                break
            batch = companies[idx: idx + max_workers]
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = {}
                for company in batch:
                    website = company.get("website")
                    name = company.get("company")
                    if not website or not name:
                        continue
                    futures[executor.submit(
                        LeadGenService.enrich_company,
                        website,
                        name,
                        LeadGenService.MAX_LEADS_PER_COMPANY,
                    )] = website

                for future in as_completed(futures):
                    if deadline is not None and time.time() >= deadline:
                        return leads
                    try:
                        results = future.result() or []
                    except Exception as exc:
                        logger.debug("Company enrichment failed: %s", exc)
                        continue
                    for candidate in results:
                        email_lower = candidate["email"].lower().strip()
                        if email_lower in exclude_set or email_lower in seen_emails:
                            continue
                        seen_emails.add(email_lower)
                        leads.append(candidate)
                        if len(leads) >= target_leads:
                            return leads
            if len(leads) >= target_leads:
                break

        return leads

    @staticmethod
    def enrich_company(
        website: str,
        company: str,
        max_candidates: Optional[int] = None,
    ) -> List[dict]:
        lead = SearchLead(
            name=company,
            website=website,
            snippet=None,
            source="leadgen_enrich",
            confidence=0.0,
        )
        target = max_candidates or LeadGenService.MAX_LEADS_PER_COMPANY
        strict, partial = LeadGenService._extract_contacts_from_lead(lead, max_candidates=target)
        results = strict + partial
        return results[:target]

    @staticmethod
    def _fetch_page(url: str) -> Optional[str]:
        try:
            headers = {"User-Agent": "Mozilla/5.0 (compatible; LeadGenBot/1.0)"}
            resp = requests.get(
                url,
                headers=headers,
                timeout=LeadGenService.CRAWL_TIMEOUT_SECONDS,
                allow_redirects=True,
            )
            resp.raise_for_status()
            return resp.text
        except Exception as exc:
            logger.debug("Failed to fetch %s: %s", url, exc)
            return None

    @staticmethod
    def _extract_contacts_from_page(
        page_url: str,
        company_name: str,
        website: str,
    ) -> Optional[Tuple[List[dict], List[dict]]]:
        html = LeadGenService._fetch_page(page_url)
        if not html:
            return None
        return LeadGenService._extract_contacts_from_html(
            html=html,
            page_url=page_url,
            company_name=company_name,
            website=website,
        )

    @staticmethod
    def _extract_contacts_from_html(
        html: str,
        page_url: str,
        company_name: str,
        website: str,
    ) -> Tuple[List[dict], List[dict]]:
        soup = BeautifulSoup(html, "html.parser")
        strict_results: List[dict] = []
        partial_results: List[dict] = []
        page_text = LeadGenService._compact_whitespace(soup.get_text(" ", strip=True))
        name_role_pairs = LeadGenService._extract_name_role_pairs(page_text)
        email_entries = LeadGenService._extract_email_entries(soup)

        for email, context in email_entries:
            is_valid, normalized = LeadService.validate_email_address(email)
            if not is_valid or not normalized:
                continue
            if LeadService.is_role_email(normalized):
                continue
            if LeadGenService._is_generic_mailbox(normalized):
                continue

            name = LeadGenService._extract_name(context, normalized)
            title = LeadGenService._extract_role(context)
            if (not name or not title) and name_role_pairs:
                name, title = LeadGenService._match_name_role_pairs(
                    name, title, normalized, name_role_pairs
                )
            if not title:
                title = LeadGenService._role_from_email(normalized)
            candidate = LeadGenService._build_candidate(
                email=normalized,
                name=name,
                title=title,
                company=company_name,
                website=website,
                source_url=page_url,
            )
            if not candidate:
                continue
            if candidate["missing_fields"]:
                partial_results.append(candidate)
            else:
                strict_results.append(candidate)

        return strict_results, partial_results

    @staticmethod
    def _build_candidate(
        email: str,
        name: Optional[Tuple[str, Optional[str]]],
        title: Optional[str],
        company: str,
        website: str,
        source_url: str,
    ) -> Optional[dict]:
        if not company:
            return None
        missing: List[str] = []
        first_name: Optional[str] = None
        last_name: Optional[str] = None
        if name:
            first_name, last_name = name
        else:
            missing.append("first_name")
        if not last_name:
            missing.append("last_name")
        if not title:
            missing.append("title")

        # Option 2: allow missing title OR missing last name (but not both).
        if "first_name" in missing:
            return None
        if "last_name" in missing and "title" in missing:
            return None

        return {
            "email": email,
            "first_name": first_name,
            "last_name": last_name,
            "company": company,
            "title": title,
            "website": website,
            "source_url": source_url,
            "missing_fields": missing,
        }

    @staticmethod
    def _extract_email_entries(soup: BeautifulSoup) -> List[Tuple[str, str]]:
        entries: List[Tuple[str, str]] = []
        for link in soup.select("a[href^='mailto:']"):
            raw = link.get("href", "")
            email = raw.replace("mailto:", "").split("?")[0].strip()
            if not email:
                continue
            context = LeadGenService._build_email_context(link)
            entries.append((email, context))

        if entries:
            return entries

        text = LeadGenService._compact_whitespace(soup.get_text(" ", strip=True))
        for match in EMAIL_RE.finditer(text):
            email = match.group(0)
            context = LeadGenService._context_window(text, email, window=160)
            entries.append((email, context))

        return entries

    @staticmethod
    def _context_window(text: str, token: str, window: int) -> str:
        lower = text.lower()
        idx = lower.find(token.lower())
        if idx == -1:
            return text[: window * 2]
        start = max(0, idx - window)
        end = min(len(text), idx + len(token) + window)
        return text[start:end].strip()

    @staticmethod
    def _extract_name(context: str, email: str) -> Optional[Tuple[str, Optional[str]]]:
        # Use email-local part to avoid mismatched names from page text.
        return LeadGenService._extract_name_from_email(email)

    @staticmethod
    def _extract_name_from_text(text: str) -> Optional[Tuple[str, Optional[str]]]:
        cleaned = EMAIL_RE.sub(" ", text)
        cleaned = LeadGenService._compact_whitespace(cleaned)
        for first, last in NAME_RE.findall(cleaned):
            if first in NAME_STOPWORDS or last in NAME_STOPWORDS:
                continue
            return first, last
        return None

    @staticmethod
    def _extract_name_from_email(email: str) -> Optional[Tuple[str, Optional[str]]]:
        local = email.split("@", 1)[0]
        local = re.sub(r"[^a-zA-Z._-]", "", local)
        for sep in [".", "_", "-"]:
            if sep in local:
                parts = [p for p in local.split(sep) if p]
                if len(parts) >= 2 and parts[0].isalpha() and parts[1].isalpha():
                    if parts[0].lower() in GENERIC_EMAIL_LOCAL or parts[1].lower() in GENERIC_EMAIL_LOCAL:
                        return None
                    first = parts[0].capitalize()
                    last = parts[1].capitalize()
                    if first in NAME_STOPWORDS or last in NAME_STOPWORDS:
                        return None
                    return first, last
        if local.isalpha() and local.lower() not in GENERIC_EMAIL_LOCAL:
            first = local.capitalize()
            if first in NAME_STOPWORDS:
                return None
            return first, None
        return None

    @staticmethod
    def _extract_name_role_pairs(text: str) -> List[Tuple[str, str, str]]:
        pairs: List[Tuple[str, str, str]] = []
        if not text:
            return pairs

        for match in NAME_RE.finditer(text):
            first, last = match.group(1), match.group(2)
            if first in NAME_STOPWORDS or last in NAME_STOPWORDS:
                continue
            start = max(0, match.start() - 80)
            end = min(len(text), match.end() + 80)
            window = text[start:end]
            role_match = ROLE_RE.search(window)
            if role_match:
                role = role_match.group(0).strip()
                pairs.append((first, last, role))

        return pairs

    @staticmethod
    def _match_name_role_pairs(
        name: Optional[Tuple[str, Optional[str]]],
        title: Optional[str],
        email: str,
        pairs: List[Tuple[str, str, str]],
    ) -> Tuple[Optional[Tuple[str, Optional[str]]], Optional[str]]:
        if not pairs:
            return name, title

        local = email.split("@", 1)[0].lower()
        for first, last, role in pairs:
            if first.lower() in local or last.lower() in local:
                return (first, last), role

        if name and not title:
            return name, pairs[0][2]
        if title and not name:
            return (pairs[0][0], pairs[0][1]), title

        return name, title

    @staticmethod
    def _role_from_email(email: str) -> Optional[str]:
        local = email.split("@", 1)[0].lower()
        tokens = re.split(r"[._-]+", local)
        role_map = {
            "owner": "Owner",
            "founder": "Founder",
            "ceo": "CEO",
            "cmo": "Chief Marketing Officer",
            "coo": "Chief Operating Officer",
            "president": "President",
            "director": "Director",
            "managing": "Managing Director",
            "manager": "Manager",
            "vp": "VP",
            "partner": "Partner",
            "principal": "Principal",
            "head": "Head",
            "lead": "Lead",
        }
        for token in tokens:
            if token in role_map:
                return role_map[token]
        return None

    @staticmethod
    def _is_generic_mailbox(email: str) -> bool:
        local = email.split("@", 1)[0].lower()
        if local in GENERIC_EMAIL_LOCAL:
            return True
        tokens = [t for t in re.split(r"[._-]+", local) if t]
        if not tokens:
            return True
        if all(t in GENERIC_EMAIL_LOCAL for t in tokens):
            return True
        return False

    @staticmethod
    def _build_email_context(link: BeautifulSoup) -> str:
        texts: List[str] = []
        node = link
        for _ in range(3):
            if not node:
                break
            text = node.get_text(" ", strip=True)
            if text:
                texts.append(text)
            node = node.parent
        heading = link.find_previous(["h1", "h2", "h3", "h4"])
        if heading:
            heading_text = heading.get_text(" ", strip=True)
            if heading_text:
                texts.append(heading_text)
        container = link.find_parent(class_=re.compile(r"(team|staff|member|person|profile|bio)", re.IGNORECASE))
        if container:
            container_text = container.get_text(" ", strip=True)
            if container_text:
                texts.append(container_text)
        return LeadGenService._compact_whitespace(" ".join(texts))

    @staticmethod
    def _extract_role(text: str) -> Optional[str]:
        match = ROLE_RE.search(text)
        if not match:
            return None
        title = match.group(0).strip()
        if not title:
            return None
        return title

    @staticmethod
    def _normalize_base_url(url: str) -> Optional[str]:
        parsed = urlparse(url)
        if not parsed.scheme:
            url = f"https://{url}"
            parsed = urlparse(url)
        if not parsed.netloc:
            return None
        return f"{parsed.scheme}://{parsed.netloc}"

    @staticmethod
    def _derive_company_name(lead_name: str, website: str) -> str:
        candidates = [lead_name]
        parsed = urlparse(website)
        domain = parsed.netloc.replace("www.", "")
        root = domain.split(".")[0].replace("-", " ")
        candidates.append(root.title())

        for candidate in candidates:
            if not candidate:
                continue
            for sep in ["|", "-", ":"]:
                if sep in candidate:
                    parts = [p.strip() for p in candidate.split(sep) if p.strip()]
                    if parts:
                        candidate = parts[-1]
                        break
            if candidate:
                return candidate.strip()
        return root.title()

    @staticmethod
    def _compact_whitespace(value: str) -> str:
        return " ".join(value.split())

    @staticmethod
    def _expand_queries(query: str) -> List[str]:
        base = query.strip()
        if not base:
            return []
        lowered = base.lower()
        agency_intent = any(k in lowered for k in AGENCY_KEYWORDS)
        variants = [
            base,
            f"{base} company",
            f"{base} business",
            f"{base} services",
            f"{base} team",
            f"{base} contact",
            f"{base} official website",
        ]
        if agency_intent:
            variants.extend(
                [
                    f"{base} agency",
                    f"{base} digital agency",
                    f"{base} creative agency",
                    f"{base} agency contact",
                ]
            )
        seen = set()
        ordered: List[str] = []
        for v in variants:
            v = LeadGenService._compact_whitespace(v)
            if v and v not in seen:
                seen.add(v)
                ordered.append(v)
        return ordered

    @staticmethod
    def _filter_list_pages(leads: List[SearchLead]) -> List[SearchLead]:
        filtered: List[SearchLead] = []
        for lead in leads:
            website = lead.website or ""
            if not website:
                continue
            parsed = urlparse(website)
            domain = parsed.netloc.lower().replace("www.", "")
            if any(
                domain == blocked or domain.endswith(f".{blocked}")
                for blocked in LIST_PAGE_DOMAINS
            ):
                continue
            if LeadGenService._is_content_domain(domain):
                continue
            haystack = " ".join(
                [
                    lead.name or "",
                    lead.snippet or "",
                    parsed.path or "",
                    parsed.query or "",
                ]
            )
            if any(pattern.search(haystack) for pattern in LIST_PAGE_PATTERNS):
                continue
            if any(pattern.search(haystack) for pattern in CONTENT_PAGE_PATTERNS):
                continue
            filtered.append(lead)
        return filtered

    @staticmethod
    def _is_content_domain(domain: str) -> bool:
        return any(
            domain == blocked or domain.endswith(f".{blocked}")
            for blocked in CONTENT_DOMAINS
        )
