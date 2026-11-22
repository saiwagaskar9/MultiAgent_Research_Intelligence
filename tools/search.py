"""
Web search tool using DuckDuckGo (ddgs) — no API key required.
"""
import logging
from typing import List, Dict
try:
    from duckduckgo_search import DDGS
except ImportError:
    from ddgs import DDGS

logger = logging.getLogger(__name__)


def web_search(query: str, max_results: int = 8) -> List[Dict]:
    """
    Search the web using DuckDuckGo.
    Returns list of {title, url, snippet} dicts.
    """
    results = []
    try:
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=max_results):
                results.append({
                    "title": r.get("title", ""),
                    "url": r.get("href", ""),
                    "snippet": r.get("body", ""),
                })
    except Exception as e:
        logger.warning(f"Web search failed for '{query}': {e}")
        # Return empty — agents will work with LLM knowledge only
    return results


def format_search_results(results: List[Dict]) -> str:
    """Format search results as readable text for LLM context."""
    if not results:
        return "No web search results available. Using internal knowledge."

    lines = ["=== Web Search Results ===\n"]
    for i, r in enumerate(results, 1):
        lines.append(f"{i}. **{r['title']}**")
        lines.append(f"   URL: {r['url']}")
        lines.append(f"   {r['snippet'][:300]}")
        lines.append("")
    return "\n".join(lines)


def multi_query_search(queries: List[str], max_per_query: int = 5) -> str:
    """Run multiple search queries and combine results."""
    all_results = []
    seen_urls = set()

    for q in queries[:4]:  # Limit to 4 queries
        results = web_search(q, max_results=max_per_query)
        for r in results:
            if r["url"] not in seen_urls:
                seen_urls.add(r["url"])
                all_results.append(r)

    return format_search_results(all_results[:15])
