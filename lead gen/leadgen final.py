import requests
from bs4 import BeautifulSoup
import csv
import json
import time
from dataclasses import dataclass, asdict
from typing import List, Optional
import urllib.parse
from ddgs import DDGS
from openai import OpenAI
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


@dataclass
class Lead:
    name: str
    website: Optional[str]
    snippet: Optional[str]
    source: str
    confidence: float


HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; LeadGenBot/1.0)"
}


def filter_with_ai(leads: List[Lead], query_type: str) -> List[Lead]:
    """Use OpenAI to filter out list pages and keep only actual business/venue pages."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("⚠️  No OPENAI_API_KEY found. Skipping AI filtering. Set it to enable smart filtering.")
        return leads
    
    client = OpenAI(api_key=api_key)
    filtered_leads = []
    
    for lead in leads:
        try:
            prompt = f"""Given this search result, determine if it's an actual {query_type} business/venue page or a list/directory page.

Title: {lead.name}
URL: {lead.website}
Snippet: {lead.snippet}

Respond with ONLY one word: "ACTUAL" if it's an actual individual business/venue page, or "LIST" if it's a list/directory/aggregate page (like "Top 10", "Best of", directories, etc).
"""
            
            response = client.chat.completions.create(
                model="gpt-4o-mini",  # Using cheaper model
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
                max_tokens=5
            )
            
            result = response.choices[0].message.content.strip().upper()
            
            if "ACTUAL" in result:
                filtered_leads.append(lead)
            else:
                print(f"  ❌ Filtered out: {lead.name}")
                
        except Exception as e:
            print(f"  ⚠️  Error filtering {lead.name}: {e}")
            # Keep the lead if there's an error
            filtered_leads.append(lead)
        
        # Small delay to avoid rate limiting
        time.sleep(0.2)
    
    return filtered_leads


def google_search(query: str, max_results: int = 10) -> List[Lead]:
    """Search using DuckDuckGo (more reliable than Google scraping)."""
    try:
        ddgs = DDGS()
        results = ddgs.text(query, max_results=max_results)
    except Exception as e:
        print(f"DuckDuckGo search error: {e}")
        return []

    leads: List[Lead] = []
    
    for result in results:
        try:
            name = result.get("title", "")
            url = result.get("href", "")
            snippet = result.get("body", "")
            
            if not name or not url:
                continue
            
            confidence = 0.6
            keywords = ["auditorium", "venue", "concert", "hall", "college", "cultural", "theatre"]
            if snippet and any(k in snippet.lower() for k in keywords):
                confidence = 0.75

            leads.append(
                Lead(
                    name=name,
                    website=url,
                    snippet=snippet,
                    source="google",
                    confidence=confidence,
                )
            )
        except Exception as e:
            continue
    
    return leads

    return leads


def bing_search(query: str, max_results: int = 10) -> List[Lead]:
    """Fallback search using Bing HTML results if DuckDuckGo is unavailable or blocked."""
    url = "https://www.bing.com/search"
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.bing.com/",
    })

    try:
        resp = session.get(url, params={"q": query}, timeout=30)
        resp.raise_for_status()
    except Exception as e:
        print(f"Bing request error: {e}")
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    items = soup.select("li.b_algo")

    if not items:
        with open("bing_debug.html", "w", encoding="utf-8") as f:
            f.write(resp.text)
        sample = resp.text[:1000].replace("\n", " ")
        print("No search results parsed from Bing. Saved bing_debug.html for inspection. Response sample:")
        print(sample)
        return []

    leads: List[Lead] = []
    for it in items[:max_results]:
        a = it.select_one("h2 a")
        snippet_tag = it.select_one(".b_caption p, .b_snippet")
        if not a:
            continue
        name = a.get_text(strip=True)
        href = a.get("href") or ""
        snippet = snippet_tag.get_text(strip=True) if snippet_tag else None

        confidence = 0.6
        keywords = ["auditorium", "venue", "concert", "hall", "college", "cultural", "theatre"]
        if snippet and any(k in snippet.lower() for k in keywords):
            confidence = 0.75

        leads.append(Lead(name=name, website=href if href.startswith("http") else None, snippet=snippet, source="bing", confidence=confidence))

    return leads


def combined_search(query: str, max_results: int = 10) -> List[Lead]:
    """Try Google first, then Bing as a fallback. Merge and dedupe by URL/title."""
    google = google_search(query, max_results)
    if google:
        return google

    print("Google returned no results — trying Bing fallback...")
    bing = bing_search(query, max_results)
    return bing


def save_results(leads: List[Lead], filename: str):
    json_file = f"{filename}.json"
    csv_file = f"{filename}.csv"
    if not leads:
        print("No leads to save.")
        return

    with open(json_file, "w", encoding="utf-8") as f:
        json.dump([asdict(l) for l in leads], f, indent=2, ensure_ascii=False)

    with open(csv_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=asdict(leads[0]).keys())
        writer.writeheader()
        for l in leads:
            writer.writerow(asdict(l))

    print(f"\n✅ Saved {len(leads)} leads:")
    print(f"   - {json_file}")
    print(f"   - {csv_file}")


def load_existing_leads(filename: str = "leads") -> set:
    """Load existing leads from JSON file and return set of URLs and names to avoid duplicates."""
    existing = set()
    json_file = f"{filename}.json"
    
    if os.path.exists(json_file):
        try:
            with open(json_file, "r", encoding="utf-8") as f:
                leads_data = json.load(f)
                for lead in leads_data:
                    # Track both URL and name to catch duplicates
                    if lead.get("website"):
                        existing.add(lead["website"].lower().strip())
                    if lead.get("name"):
                        existing.add(lead["name"].lower().strip())
            print(f"📋 Loaded {len(leads_data)} existing leads from {json_file}")
        except Exception as e:
            print(f"⚠️  Could not load existing leads: {e}")
    
    return existing


def main():
    print("\n=== Outreach Lead Generator ===\n")

    query = input("What type of leads are you looking for?\n> ").strip()
    location = input("\nLocation (city / region / country):\n> ").strip()

    full_query = f"{query} {location}".strip()
    print(f"\n🔎 Searching for: {full_query}\n")

    # Load existing leads to avoid duplicates
    existing_leads = load_existing_leads("leads")

    # Search for up to 15 initial promising leads, but stop early if we find 5 final proper leads
    MAX_INITIAL_LEADS = 15
    TARGET_FINAL_LEADS = 5
    final_leads = []
    
    print(f"Searching up to {MAX_INITIAL_LEADS} leads (will stop early if {TARGET_FINAL_LEADS} new proper leads found)...\n")
    
    leads = combined_search(full_query, max_results=MAX_INITIAL_LEADS)

    if not leads:
        print("❌ No leads found.")
        return
    
    # Filter results using AI to remove list pages
    print(f"\n🤖 Filtering results with AI to remove list pages (will stop after finding {TARGET_FINAL_LEADS} actual businesses)...\n")
    
    for i, lead in enumerate(leads, 1):
        # Skip if lead already exists
        if lead.website and lead.website.lower().strip() in existing_leads:
            print(f"  ⏭️  Skipped (already exists): {lead.name}")
            continue
        if lead.name and lead.name.lower().strip() in existing_leads:
            print(f"  ⏭️  Skipped (already exists): {lead.name}")
            continue
        
        try:
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                print("⚠️  No OPENAI_API_KEY found. Skipping AI filtering. Set it to enable smart filtering.")
                final_leads.append(lead)
                if len(final_leads) >= TARGET_FINAL_LEADS:
                    break
                continue
            
            client = OpenAI(api_key=api_key)
            prompt = f"""Given this search result, determine if it's an actual {query} business/venue page or a list/directory page.

Title: {lead.name}
URL: {lead.website}
Snippet: {lead.snippet}

Respond with ONLY one word: "ACTUAL" if it's an actual individual business/venue page, or "LIST" if it's a list/directory/aggregate page (like "Top 10", "Best of", directories, etc).
"""
            
            response = client.chat.completions.create(
                model="gpt-4o-mini",  # Using cheaper model
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
                max_tokens=5
            )
            
            result = response.choices[0].message.content.strip().upper()
            
            if "ACTUAL" in result:
                final_leads.append(lead)
                print(f"  ✅ Found actual business ({len(final_leads)}/{TARGET_FINAL_LEADS}): {lead.name}")
            else:
                print(f"  ❌ Filtered out: {lead.name}")
                
        except Exception as e:
            print(f"  ⚠️  Error filtering {lead.name}: {e}")
            # Keep the lead if there's an error
            final_leads.append(lead)
        
        # Small delay to avoid rate limiting
        time.sleep(0.2)
        
        # Stop if we've found enough proper leads
        if len(final_leads) >= TARGET_FINAL_LEADS:
            print(f"\n✨ Found {TARGET_FINAL_LEADS} new proper leads! Stopping search.\n")
            break
    
    if not final_leads:
        print("❌ No new actual business pages found after filtering.")
        return
    
    # Delete existing leads files
    print("\n--- Deleting existing leads files ---\n")
    if os.path.exists("leads.json"):
        os.remove("leads.json")
        print("🗑️  Deleted leads.json")
    if os.path.exists("leads.csv"):
        os.remove("leads.csv")
        print("🗑️  Deleted leads.csv")
    
    # Print results to console (only name and website)
    print("\n--- New Leads ---\n")
    for l in final_leads:
        # website may be None
        site = l.website or "(no website)"
        print(f"- {l.name} | {site}")

    # Save to a fixed filename (will create fresh files)
    filename = "leads"
    save_results(final_leads, filename)


if __name__ == "__main__":
    main()
