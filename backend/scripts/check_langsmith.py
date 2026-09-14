"""One-off diagnostic: check LangSmith configuration and connectivity.

Run from the repo root (backend dir) so it picks up the same venv/env as the app.
Usage:  python scripts/check_langsmith.py
"""
import os
import sys
import time
from datetime import datetime, timezone

# Ensure app modules are importable
sys.path.insert(0, os.path.dirname(__file__))

from app.core.config import settings


def mask_key(raw: str | None, prefix_len: int = 4, suffix_len: int = 4) -> str:
    """Return a masked version of an API key for display."""
    if not raw:
        return "<not set>"
    if len(raw) <= prefix_len + suffix_len:
        return "*" * len(raw)
    return raw[:prefix_len] + "*" * (len(raw) - prefix_len - suffix_len) + raw[-suffix_len:]


def main():
    print("=== LangSmith environment check ===\n")

    # 1. Env vars
    key = os.environ.get("LANGCHAIN_API_KEY") or os.environ.get("LANGSMITH_API_KEY")
    project = os.environ.get("LANGCHAIN_PROJECT")
    tracing = os.environ.get("LANGCHAIN_TRACING_V2")
    print(f"LANGCHAIN_API_KEY: {mask_key(key)}")
    print(f"LANGSMITH_API_KEY: {mask_key(key)}")  # may be alias
    print(f"LANGCHAIN_PROJECT: {project or '<not set>'}")
    print(f"LANGCHAIN_TRACING_V2: {tracing or '<not set>'}\n")

    # 2. Config object
    print(f"settings.langchain_api_key: {mask_key(settings.langchain_api_key)}")
    print(f"settings.langchain_project: {settings.langchain_project or '<not set>'}")
    print()

    # 3. Attempt a real LangSmith query
    from langsmith import Client
    start = time.time()

    project_name = settings.langchain_project or os.environ.get("LANGCHAIN_PROJECT") or "<default>"
    try:
        client = Client()
        runs = client.list_runs(project_name=project_name, limit=1)
        elapsed = time.time() - start
        print(f"list_runs succeeded in {elapsed:.2f}s")
        print(f"   Project: {project_name}")
        print(f"   Result count: {len(list(runs))}")
        # Show first run name if available
        runs_list = list(runs)
        if runs_list:
            first = runs_list[0]
            print(f"   First run name: {getattr(first, 'name', 'N/A')}")
            print(f"   First run error: {getattr(first, 'error', 'N/A')}")
    except Exception as e:
        elapsed = time.time() - start
        print(f"list_runs failed in {elapsed:.2f}s")
        print(f"   Exception type: {type(e).__name__}")
        print(f"   Exception message: {e}")
        import traceback
        print("   Full traceback:")
        traceback.print_exc()


if __name__ == "__main__":
    main()