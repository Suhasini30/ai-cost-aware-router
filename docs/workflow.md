# Application Workflow & Execution Mechanics

> **Cost-Aware Multi-Model AI Router**

---

## 1. Complete Request Flowchart

The flowchart below illustrates how user requests move through classification, routing, execution, reliability failover, quality judging, escalation, persistence, and telemetry:

```mermaid
flowchart TD
    A["1. User Request"] --> B["2. Clerk Authentication (getToken)"]
    B --> C["3. FastAPI Gateway (/router/ask)"]
    C --> D["4. Prompt Validation Guard"]
    D --> E{"5. Deterministic Rule Engine"}

    E -->|"Obvious Match (e.g. short QA)"| F["6. Routing Policy"]
    E -->|"Uncertain / Complex Prompt"| G["5b. LLM Classifier Agent"]
    G -->|"Task Type & Complexity"| F

    F --> H["7. Select Cheapest Capable Model"]
    H --> I["8. Primary Model Execution"]

    I -->|"429 Rate Limit / 5xx Outage"| J{"Retry Engine"}
    J -->|"Retry < 2 times"| I
    J -->|"Retries Exhausted"| K["8b. Provider Failover (Alternative Provider)"]
    K --> L["Model Answer Text"]
    I -->|"Success"| L

    L --> M{"9. Selective Quality Judge"}
    M -->|"Passed (Score >= 0.70)"| N["10. Final Answer"]
    M -->|"Failed (Score < 0.70)"| O{"Strong Model Available?"}
    
    O -->|"Yes"| P["9b. Strong Model Escalation Pass"]
    P --> N
    O -->|"No"| N

    N --> Q["11. Cost & Savings Calculation"]
    Q --> R[("12. Async MongoDB Persistence (query_logs)")]
    Q --> S["13. Send Telemetry to LangSmith"]
    Q --> T["14. Return JSON to Next.js UI"]
```

---

## 2. Detailed Stage Breakdown

### A. Simple Request (Rules Engine Match)
* **Trigger:** Prompts under 80 characters (e.g., `"What is the capital of France?"`, `"Define API"`) or matching deterministic regex rules.
* **Execution:** Processed by `rules/local`.
* **LLM API Calls:** `routing_api_calls = 0`.
* **Cost Impact:** Zero classification cost. Execution goes straight to the cheapest capable model (`FAST` tier).

### B. Ambiguous Request (LLM Classifier Agent)
* **Trigger:** Complex, long, or multi-faceted prompts that do not match rule heuristics.
* **Execution:** Handled by `classify_prompt()`. The prompt is sent to `mistral-large-latest` (or configured classifier provider).
* **Output:** Returns task type (e.g., `code_generation`, `complex_reasoning`), required capability, complexity level (`low`, `medium`, `high`), and confidence score.
* **LLM API Calls:** `routing_api_calls = 1`.

### C. Complex Request (Routing Policy)
* **Trigger:** Classifier identifies task as `complex_reasoning` or `coding` with `high` complexity.
* **Execution:** `route_decision()` filters candidate models in the registry supporting `reasoning` or `code` capabilities.
* **Policy Selection:** Selects the cheapest model meeting the `STRONG` tier capability requirement.

### D. Provider Failure (Retries & Failover)
* **Trigger:** Target provider returns HTTP 429 (rate limit), 5xx (server error), or connection timeout.
* **Execution:** Handled inside `app.reliability`:
  1. **Retries:** Retries same provider up to `reliability_max_retries` (2) with backoff base `reliability_backoff_base_s` (0.5s).
  2. **Failover:** If retries fail, switches to an alternative provider offering a model with matching capabilities.
  3. **Tracking:** Sets `transport_fallback = True` on `AskResponse`.

### E. Quality Failure & Strong-Model Escalation
* **Trigger:** `evaluate_answer()` returns a quality score below `quality_pass_threshold` (0.70) or `passed = False`.
* **Execution:**
  1. Pipeline looks up `strongest_capable(decision)`.
  2. Executes the prompt on the strongest capable model (e.g., `mistral-strong` / `groq-strong`).
  3. Re-evaluates final answer for score reporting.
  4. **Single Escalation Limit:** Strict invariant prevents any second escalation pass (`max_escalations = 1`).
  5. **Tracking:** Sets `escalated = True`, `escalation_reason = "quality_gate_failed"`, and `model_api_calls = 2`.

---

## 3. Cost & Metrics Tracking

### Cost Calculation (`app/cost/calculator.py`)
Cost is computed per execution leg using token prices from `ModelSpec`:

```text
Leg Cost = (Input Tokens / 1000 * input_cost_per_1k) + (Output Tokens / 1000 * output_cost_per_1k)
```

* **`actual_cost`:** Sum of costs across all executed legs (including classification if billed, primary execution, and escalation execution if triggered).
* **`baseline_cost`:** Estimated cost if the prompt had been routed directly to the strongest capable model (`strongest_capable`) from the start.
* **`savings`:** `baseline_cost - actual_cost`
* **`savings_pct`:** `((baseline_cost - actual_cost) / baseline_cost) * 100`

### API-Call Tracking Definitions
* **`routing_api_calls`:** Number of LLM API calls spent performing classification (0 for rule engine, 1 for LLM classifier agent).
* **`model_api_calls`:** Number of LLM API calls spent generating model answers (1 for standard run, 2 if quality escalation occurred).
* **`total_llm_api_calls`:** Total API calls for the entire request (`routing_api_calls + model_api_calls`).
