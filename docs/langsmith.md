# LangSmith Observability & Tracing Integration

> **Cost-Aware Multi-Model AI Router**

---

## 1. What is LangSmith?

**LangSmith** is an observability platform designed by LangChain to trace, monitor, and debug LLM application execution.

In this project, LangSmith is used to capture hierarchical execution traces of the router pipeline—including classification decisions, model latency, token counts, quality evaluation scores, and escalation events—without adding latency to user requests or introducing dependencies into inference models.

---

## 2. Step-by-Step LangSmith Setup

1. **Create Account:** Go to [smith.langchain.com](https://smith.langchain.com/) and create or sign into an account.
2. **Create Project:** Navigate to **Projects** and create a project named `cost-aware-router`.
3. **Generate API Key:** Go to **Settings** $\rightarrow$ **API Keys** and generate a personal access token (starts with `lsv2_pt_...`).

---

## 3. Environment Variables

Inspect the actual backend configuration (`backend/app/core/config.py` & `.env.example`):

```env
# Enable LangSmith V2 tracing format
LANGCHAIN_TRACING_V2=true

# LangSmith API Key (telemetry only)
LANGCHAIN_API_KEY=lsv2_pt_...

# Alternative alias accepted by script diagnostics
LANGSMITH_API_KEY=lsv2_pt_...

# LangSmith project name in dashboard
LANGCHAIN_PROJECT=cost-aware-router
```

---

## 4. Connection & Tracing Architecture

```mermaid
flowchart TD
    Env[Environment Variables: LANGCHAIN_API_KEY] --> Setup[setup_tracing app/core/tracing.py]
    Setup -->|Set OS Env Vars| SDK[LangSmith Python SDK]
    
    FastAPI[FastAPI Application Startup] --> Setup
    
    subgraph Execution Points
        Pipeline[answer_prompt] -->|@traceable name=router-ask-pipeline| SDK
        Classifier[classify_prompt] -->|@traceable| SDK
        Adapter[execute] -->|@traceable| SDK
        Judge[evaluate_answer] -->|@traceable| SDK
    end
    
    SDK -->|Async Telemetry Spans| Cloud[LangSmith Dashboard Cloud]
```

### Trace Setup Code (`backend/app/core/tracing.py`)
During startup in `app/main.py`, `setup_tracing(settings)` mirrors Pydantic settings into system environment variables so the LangSmith SDK can automatically pick them up:

```python
def setup_tracing(app_settings: Settings) -> bool:
    key = app_settings.langchain_api_key
    if not key:
        return False
    os.environ["LANGCHAIN_TRACING_V2"] = "true" if app_settings.langchain_tracing_v2 else "false"
    os.environ["LANGCHAIN_API_KEY"] = key
    os.environ["LANGCHAIN_PROJECT"] = app_settings.langchain_project
    return True
```

---

## 5. Workflow & Observed Data

When a user submits a query to `/router/ask`, LangSmith records a nested tree of spans:

```text
└─ router-ask-pipeline (Root Span)
   ├─ classify_prompt (Child Span)
   │  └─ LLM Call: mistral-large-latest (Inputs, Outputs, Tokens, Latency)
   ├─ execute: groq-fast (Child Span)
   │  └─ LLM Call: openai/gpt-oss-20b (Prompt, Completion, Tokens, Latency)
   ├─ evaluate_answer (Child Span)
   │  └─ Quality Heuristic Judge (Score: 0.88, Passed: True)
   └─ Root Response Assembly (Actual Cost: $0.000158, Savings: 92.5%)
```

### What can be observed in LangSmith:
* **Root Latency:** Total milliseconds elapsed from request start to finish.
* **Classifier Decision:** Task type (`general_qa`, `coding`, etc.), complexity rating, confidence score.
* **Provider LLM Calls:** Prompts and generated text sent to Groq, Mistral, or Gemini APIs.
* **Token Usage:** Input and output token counts for each individual model invocation.
* **Quality Score:** Score assigned by the quality evaluator and whether escalation was triggered.
* **Exceptions & Retries:** 429 rate limits or provider failover attempts.

---

## 6. Practical Developer Walkthrough

To verify and inspect traces locally:

1. Add your `LANGCHAIN_API_KEY` to `backend/.env`.
2. Start the backend server:
   ```bash
   cd backend
   python server.py
   ```
3. Run the built-in diagnostic script:
   ```bash
   python scripts/check_langsmith.py
   ```
4. Submit a query via the Next.js console or via cURL:
   ```bash
   curl -X POST http://127.0.0.1:8000/router/ask \
     -H "Content-Type: application/json" \
     -H "Authorization: Bearer <your_token>" \
     -d '{"prompt": "Explain RAG vs Fine-tuning with an example."}'
   ```
5. Open [smith.langchain.com](https://smith.langchain.com/), select the `cost-aware-router` project, and view the live trace details.

---

## 7. Production Setup (Render)

To enable LangSmith in production on Render:

1. Open your Render Web Service dashboard.
2. Under **Environment Variables**, add:
   * `LANGCHAIN_TRACING_V2`: `true`
   * `LANGCHAIN_API_KEY`: `<your-langsmith-key>`
   * `LANGCHAIN_PROJECT`: `cost-aware-router`
3. Deploy or restart the Web Service.

---

## 8. Security & Privacy Controls

* **Key Isolation Guarantee:** `LANGCHAIN_API_KEY` is used strictly by the LangSmith SDK for telemetry. It is never passed as an authorization header to LLM inference providers.
* **Classifier Isolation:** The classifier model agent never receives the LangSmith API key.
* **Privacy Flags (`app/core/config.py`):**
  * `privacy_store_prompts`: Controls whether prompts are recorded in history logs.
  * `privacy_store_answers`: Controls whether generated completions are recorded in history logs.

---

## 9. Troubleshooting Common Issues

* **Traces Not Appearing in Dashboard:**
  * **Cause:** `LANGCHAIN_API_KEY` is empty or invalid in `.env`.
  * **Fix:** Run `python scripts/check_langsmith.py` to test connectivity.
* **Traces Sent to "default" Project:**
  * **Cause:** `LANGCHAIN_PROJECT` variable is missing.
  * **Fix:** Set `LANGCHAIN_PROJECT=cost-aware-router` in environment settings.
* **Backend Crashing When LangSmith Is Offline:**
  * **Cause:** N/A (`langsmith` imports in `app/execution/base.py` use `try/except` wrappers; failure to reach LangSmith never fails user requests).
