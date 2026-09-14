#!/usr/bin/env python3
"""
Model Registry Drift Check

Scheduled task to verify model pricing against live provider pricing pages
using the Parallel Search MCP (web_search + web_fetch).

Usage: python scripts/check_model_registry.py

Outputs a diff report to registry_drift_report.json
"""

import json
import sys
import time
import asyncio
import httpx
from pathlib import Path
from typing import Any
from dataclasses import dataclass, asdict
from urllib.parse import urljoin

# Ensure app modules are importable
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.models.registry import REGISTRY, Provider, ModelSpec

MCP_ENDPOINT = "https://search.parallel.ai/mcp"
REPORT_PATH = Path(__file__).parent.parent / "registry_drift_report.json"

# Provider pricing page URLs (known official pages)
PROVIDER_PRICING_URLS = {
    Provider.MISTRAL: "https://mistral.ai/pricing/",
    Provider.GEMINI: "https://ai.google.dev/pricing",
    Provider.GROQ: "https://groq.com/pricing/",
}

# Known model ID mappings (registry api_id -> provider's page model identifier)
MODEL_ID_MAP = {
    # Mistral
    "mistral-small-latest": ["mistral-small", "mistral-small-2409", "mistral small"],
    "mistral-large-latest": ["mistral-large", "mistral-large-2411", "mistral large"],
    # Gemini - note: registry uses gemini-3.6-flash for both fast/strong
    "gemini-3.6-flash": ["gemini-1.5-flash", "gemini-1.5-flash-8b", "gemini flash"],
    "gemini-1.5-pro": ["gemini-1.5-pro", "gemini-pro"],
    # Groq
    "openai/gpt-oss-20b": ["gpt-oss-20b", "gpt-oss 20b"],
    "qwen/qwen3.6-27b": ["qwen-2.5-27b", "qwen 2.5 27b", "qwen2.5-27b"],
}


@dataclass
class PricingInfo:
    model_name: str
    input_per_1k: float | None
    output_per_1k: float | None
    source_url: str


@dataclass
class DiffEntry:
    model: str
    registry_input_per_1k: float
    registry_output_per_1k: float
    live_input_per_1k: float | None
    live_output_per_1k: float | None
    mismatch: bool
    notes: str = ""


class ParallelSearchMCP:
    """Client for Parallel Search MCP (web_search + web_fetch)."""

    def __init__(self, endpoint: str = MCP_ENDPOINT, timeout: float = 30.0):
        self.endpoint = endpoint
        self.timeout = timeout
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self):
        self._client = httpx.AsyncClient(timeout=self.timeout)
        return self

    async def __aexit__(self, *args):
        if self._client:
            await self._client.aclose()

    async def _call(self, method: str, params: dict) -> dict:
        """Make a JSON-RPC call to the MCP endpoint."""
        if not self._client:
            raise RuntimeError("Client not initialized. Use async context manager.")
        payload = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params,
            "id": int(time.time() * 1000) % 100000,
        }
        resp = await self._client.post(self.endpoint, json=payload)
        resp.raise_for_status()
        data = resp.json()
        if "error" in data:
            raise RuntimeError(f"MCP error: {data['error']}")
        return data.get("result", {})

    async def web_search(self, query: str, max_results: int = 5) -> list[dict]:
        """Search the web and return results with URLs."""
        result = await self._call("tools/call", {
            "name": "web_search",
            "arguments": {"query": query, "max_results": max_results}
        })
        # Result format depends on MCP implementation
        content = result.get("content", [])
        if isinstance(content, str):
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                return [{"text": content, "url": ""}]
        return content if isinstance(content, list) else [content]

    async def web_fetch(self, url: str, max_chars: int = 8000) -> str:
        """Fetch and return page content as text."""
        result = await self._call("tools/call", {
            "name": "web_fetch",
            "arguments": {"url": url, "max_chars": max_chars}
        })
        content = result.get("content", "")
        if isinstance(content, list):
            return "\n".join(str(c) for c in content)
        return str(content)


def extract_pricing_from_text(text: str, provider: Provider) -> list[PricingInfo]:
    """Extract pricing info from fetched page text. Heuristic-based."""
    import re

    results: list[PricingInfo] = []
    text_lower = text.lower()

    # Common patterns for pricing (per 1M tokens typically on provider pages)
    # Pattern: $X.XX per 1M input / $Y.YY per 1M output
    # or $X.XX / 1M tokens

    # Provider-specific extraction
    if provider == Provider.MISTRAL:
        # Mistral pricing page typically has tables with model names and prices
        # Look for patterns like "mistral-small" + price
        patterns = [
            r"(mistral-small[^\n]*?)[\s\$]*([\d.]+)\s*(?:per|/)\s*1?\s*[mk]\s*(?:input|output)?",
            r"(mistral-large[^\n]*?)[\s\$]*([\d.]+)\s*(?:per|/)\s*1?\s*[mk]\s*(?:input|output)?",
        ]
        # Simplified: look for price tables
        for model_key in ["mistral-small", "mistral-large"]:
            if model_key in text_lower:
                # Find nearby numbers that look like prices
                idx = text_lower.index(model_key)
                window = text[idx:idx+500]
                prices = re.findall(r'\$?(\d+\.\d+)', window)
                if len(prices) >= 2:
                    results.append(PricingInfo(
                        model_name=model_key,
                        input_per_1k=float(prices[0]) / 1000 if float(prices[0]) > 1 else float(prices[0]),
                        output_per_1k=float(prices[1]) / 1000 if float(prices[1]) > 1 else float(prices[1]),
                        source_url=""
                    ))

    elif provider == Provider.GEMINI:
        # Gemini pricing: typically $0.075/1M input, $0.30/1M output for Flash
        # $1.25/1M input, $5.00/1M output for Pro
        for model_key in ["gemini-1.5-flash", "gemini-1.5-pro", "gemini flash", "gemini pro"]:
            if model_key in text_lower:
                idx = text_lower.index(model_key)
                window = text[idx:idx+500]
                prices = re.findall(r'\$?(\d+\.\d+)', window)
                if len(prices) >= 2:
                    results.append(PricingInfo(
                        model_name=model_key,
                        input_per_1k=float(prices[0]) / 1000,
                        output_per_1k=float(prices[1]) / 1000,
                        source_url=""
                    ))

    elif provider == Provider.GROQ:
        # Groq typically has very low pricing
        for model_key in ["gpt-oss", "qwen", "llama", "mixtral"]:
            if model_key in text_lower:
                idx = text_lower.index(model_key)
                window = text[idx:idx+500]
                prices = re.findall(r'\$?(\d+\.\d+)', window)
                if len(prices) >= 2:
                    results.append(PricingInfo(
                        model_name=model_key,
                        input_per_1k=float(prices[0]) / 1000,
                        output_per_1k=float(prices[1]) / 1000,
                        source_url=""
                    ))

    # Fallback: generic price extraction from tables
    if not results:
        # Look for tables with model names and prices
        table_pattern = r'(?:model|name)[^\n]*\n[^\n]*\|[^\n]*\$[\d.]+'
        matches = re.findall(table_pattern, text_lower, re.IGNORECASE)
        for match in matches[:10]:
            # Very rough extraction
            prices = re.findall(r'\$?(\d+\.\d+)', match)
            if len(prices) >= 2:
                model_match = re.search(r'(?:gemini|mistral|gpt|qwen|llama)[^\s|]*', match, re.IGNORECASE)
                if model_match:
                    results.append(PricingInfo(
                        model_name=model_match.group(0),
                        input_per_1k=float(prices[0]) / 1000 if float(prices[0]) > 1 else float(prices[0]),
                        output_per_1k=float(prices[1]) / 1000 if float(prices[1]) > 1 else float(prices[1]),
                        source_url=""
                    ))

    return results


def find_model_pricing(pricing_list: list[PricingInfo], registry_model: ModelSpec) -> PricingInfo | None:
    """Match a registry model to extracted pricing info."""
    api_id = registry_model.api_id
    # Check direct mapping
    search_terms = MODEL_ID_MAP.get(api_id, [api_id])
    # Also check display name and id
    search_terms.extend([registry_model.id.lower(), registry_model.display_name.lower()])

    for pricing in pricing_list:
        for term in search_terms:
            if term.lower() in pricing.model_name.lower():
                return pricing
    return None


async def check_provider(mcp: ParallelSearchMCP, provider: Provider) -> tuple[list[PricingInfo], str]:
    """Check pricing for a single provider."""
    url = PROVIDER_PRICING_URLS.get(provider)
    if not url:
        return [], f"No pricing URL for {provider.value}"

    print(f"  Checking {provider.value} at {url}...")
    try:
        content = await mcp.web_fetch(url)
        print(f"    Fetched {len(content)} chars")
        pricing = extract_pricing_from_text(content, provider)
        print(f"    Extracted {len(pricing)} model prices")
        return pricing, ""
    except Exception as e:
        print(f"    Error: {e}")
        return [], str(e)


def compare_prices(registry: ModelSpec, live: PricingInfo | None) -> DiffEntry:
    """Compare registry prices with live prices."""
    if live is None:
        return DiffEntry(
            model=registry.id,
            registry_input_per_1k=registry.input_cost_per_1k,
            registry_output_per_1k=registry.output_cost_per_1k,
            live_input_per_1k=None,
            live_output_per_1k=None,
            mismatch=True,
            notes="Model not found on provider pricing page (possibly deprecated/renamed)"
        )

    # Convert live prices from per-1M to per-1K if needed
    # Heuristic: if price > 1, it's likely per-1M
    live_in = live.input_per_1k
    live_out = live.output_per_1k
    if live_in and live_in > 1:
        live_in = live_in / 1000
    if live_out and live_out > 1:
        live_out = live_out / 1000

    mismatch = False
    notes = []
    if live_in is not None and abs(live_in - registry.input_cost_per_1k) > 0.0001:
        mismatch = True
        notes.append(f"input: registry={registry.input_cost_per_1k:.6f} vs live={live_in:.6f}")
    if live_out is not None and abs(live_out - registry.output_cost_per_1k) > 0.0001:
        mismatch = True
        notes.append(f"output: registry={registry.output_cost_per_1k:.6f} vs live={live_out:.6f}")

    return DiffEntry(
        model=registry.id,
        registry_input_per_1k=registry.input_cost_per_1k,
        registry_output_per_1k=registry.output_cost_per_1k,
        live_input_per_1k=live_in,
        live_output_per_1k=live_out,
        mismatch=mismatch,
        notes="; ".join(notes) if notes else "OK"
    )


async def main():
    print("=== Model Registry Drift Check ===\n")
    print(f"Registry has {len(REGISTRY)} models\n")

    all_diffs: list[DiffEntry] = []
    errors: list[str] = []

    async with ParallelSearchMCP() as mcp:
        # Check each provider
        for provider in Provider:
            print(f"\n--- {provider.value.upper()} ---")
            pricing_list, err = await check_provider(mcp, provider)
            if err:
                errors.append(f"{provider.value}: {err}")

            # Get registry models for this provider
            provider_models = [m for m in REGISTRY.values() if m.provider == provider]

            for model in provider_models:
                live = find_model_pricing(pricing_list, model)
                diff = compare_prices(model, live)
                all_diffs.append(diff)
                status = "MISMATCH" if diff.mismatch else "OK"
                print(f"  {model.id}: {status}")
                if diff.notes and diff.notes != "OK":
                    print(f"    {diff.notes}")

    # Generate report
    report = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "total_models": len(REGISTRY),
        "mismatches": sum(1 for d in all_diffs if d.mismatch),
        "errors": errors,
        "diffs": [asdict(d) for d in all_diffs],
    }

    # Write report
    with open(REPORT_PATH, "w") as f:
        json.dump(report, f, indent=2)

    print(f"\n=== SUMMARY ===")
    print(f"Total models checked: {len(all_diffs)}")
    print(f"Mismatches found: {report['mismatches']}")
    print(f"Errors: {len(errors)}")
    print(f"Report written to: {REPORT_PATH}")

    # Print mismatches
    for d in all_diffs:
        if d.mismatch:
            print(f"  - {d.model}: {d.notes}")

    # Exit with non-zero if mismatches found (for CI integration)
    sys.exit(1 if report["mismatches"] > 0 else 0)


if __name__ == "__main__":
    asyncio.run(main())