# User Query Execution Workflow

> **Step-by-Step Lifecycle of a User Request**

---

## 1. Concrete Example Request

Consider a user submitting the following prompt in the interactive console:

> **"Explain RAG vs Fine-tuning with an example."**

---

## 2. End-to-End Component Flow

```mermaid
flowchart TD
    UserPrompt["User Prompt"] --> ConsoleUI["1. Next.js Console (app/console/page.tsx)"]
    ConsoleUI -->|"getToken"| ClerkAuth["2. Clerk Auth Session"]
    ClerkAuth -->> ConsoleUI: "JWT Token"
    ConsoleUI -->|"POST /router/ask"| FastAPI["3. FastAPI Backend (main.py)"]
    FastAPI --> AuthDep["4. Auth Dependency (get_current_user_id)"]
    AuthDep --> Validation["5. Prompt Guard (_validate_prompt)"]
    Validation --> RuleEngine{"6. Rule Engine (rules/local)"}
    RuleEngine -->|"Inconclusive"| Classifier["7. LLM Classifier Agent (classify_prompt)"]
    Classifier --> Policy["8. Routing Policy (route_decision)"]
    Policy --> ModelAdapter["9. Model Adapter (execute)"]
    ModelAdapter --> QualityJudge{"10. Quality Judge (evaluate_answer)"}
    QualityJudge -->|"PASS"| RespBuild["11. Build AskResponse"]
    QualityJudge -->|"FAIL"| StrongModel["10b. Strong Model Escalation"]
    StrongModel --> RespBuild
    RespBuild --> MongoStore[("12. MongoDB Persist (persist_ask_response)")]
    RespBuild --> ConsoleRender["13. Render Result Cards"]
```

---

## 3. Step-by-Step Execution Breakdown

### Step 1: User Prompt Input & State Change
* **Component:** `frontend/app/console/page.tsx` (`PromptCard`)
* **Action:** User types `"Explain RAG vs Fine-tuning with an example."` and clicks **Run Router**.
* **State:** `setRunning(true)` renders `<SkeletonCard />` loading indicators across the console layout.
* **Cost:** $0.00 | **LLM API Calls:** 0

### Step 2: Session Token Fetching
* **Component:** Clerk React SDK (`useAuth()`)
* **Action:** `await getToken()` retrieves a fresh RS256 JWT session token.
* **Cost:** $0.00 | **LLM API Calls:** 0

### Step 3 & 4: API Dispatch & Authentication
* **Component:** `frontend/lib/api.ts` -> `backend/app/auth/dependencies.py`
* **Action:** Client sends HTTP POST to `/router/ask` with `Authorization: Bearer <jwt>`. Backend extracts token `kid`, looks up key in JWKS cache, and validates signature/claims.
* **Cost:** $0.00 | **LLM API Calls:** 0

### Step 5: Prompt Validation Guard
* **Component:** `_validate_prompt()` in `backend/app/router/router.py`
* **Action:** Verifies prompt is non-empty and under `max_prompt_chars` (4000).
* **Cost:** $0.00 | **LLM API Calls:** 0

### Step 6: Deterministic Rule Engine Check
* **Component:** `backend/app/router/agent.py` (`rules/local`)
* **Action:** Checks prompt length (44 chars) and regex patterns. Prompt asks for a comparative explanation ("RAG vs Fine-tuning"), which is not an obvious single-word definition. Rule engine marks prompt as requiring LLM classification.
* **Cost:** $0.00 | **LLM API Calls:** 0

### Step 7: LLM Classifier Agent Execution
* **Component:** `classify_prompt()` in `backend/app/router/agent.py`
* **Action:** Sends prompt to `mistral-large-latest` (or classifier provider) to assess task type and complexity.
* **Result:** `task_type = "general_qa"`, `complexity = "medium"`, `capability = "text"`, `confidence = 0.90`.
* **Cost:** ~$0.00005 USD | **LLM API Calls:** 1 (`routing_api_calls = 1`)

### Step 8: Routing Policy Model Selection
* **Component:** `route_decision()` in `backend/app/router/policy.py`
* **Action:** Queries registry for enabled models supporting `chat`/`text`. Orders candidate models by token price:
  1. `groq-fast` (`openai/gpt-oss-20b`) — Input: $0.20/1M, Output: $0.30/1M (Cheapest)
  2. `mistral-fast` (`mistral-small-latest`) — Input: $0.10/1M, Output: $0.30/1M
* **Selection:** `groq-fast` selected as cheapest capable model.
* **Cost:** $0.00 | **LLM API Calls:** 0

### Step 9: Primary Model Execution
* **Component:** `execute()` in `backend/app/execution/groq.py`
* **Action:** Invokes Groq API with system prompt tailored for comparison questions (requests compact comparison structure).
* **Output:** Generates a structured response text explaining RAG vs Fine-tuning with an example.
* **Tokens Used:** 120 input tokens, 280 output tokens.
* **Cost:** ~$0.000108 USD | **LLM API Calls:** 1 (`model_api_calls = 1`)

### Step 10: Selective Quality Evaluation
* **Component:** `evaluate_answer()` in `backend/app/eval/evaluator.py`
* **Action:** Evaluates answer structure, completeness, and length against heuristics.
* **Result:** `QualityVerdict(passed=True, quality_score=0.88)`.
* **Escalation:** Passed score exceeds `quality_pass_threshold` (0.70). Escalation is skipped (`escalated = False`).
* **Cost:** $0.00 | **LLM API Calls:** 0

### Step 11: Cost Leg Calculation & Response Assembly
* **Component:** `build_cost()` in `backend/app/cost/calculator.py`
* **Action:** Computes actual cost ($0.000158) vs baseline cost if strong model (`groq-strong`) was used ($0.002120). Calculates cost saved ($0.001962) and savings percentage (92.5%). Assembles `AskResponse`.
* **Cost:** $0.00 | **LLM API Calls:** 0

### Step 12: Async MongoDB Persistence
* **Component:** `persist_ask_response()` in `backend/app/history/service.py`
* **Action:** Scheduled via FastAPI `BackgroundTasks`. Writes `QueryLogDocument` into MongoDB collection `query_logs`.
* **Cost:** $0.00 | **LLM API Calls:** 0

### Step 13: UI Console Rendering
* **Component:** `ResultCard` in `frontend/app/console/page.tsx`
* **Action:** Renders sub-components: `AnswerCard` (markdown text), `RouterDetails` (task/complexity), `TraceTimeline` (stage breakdown), `SummaryGrid` (tokens/latency), `CostCard` (savings), `ReliabilityCard` (provider health).
* **Cost:** $0.00 | **LLM API Calls:** 0

---

## 4. Three Concrete Scenarios

### Scenario 1 — Cheap Model Succeeds (Standard Run)
```text
User Prompt: "What is the boiling point of water?"
 ->
Rules Engine: Obvious simple QA (len < 80 chars) -> decision: simple_qa (0 routing calls)
 ->
Policy Selection: mistral-fast (cheapest capable)
 ->
Primary Execution: Responds "100°C (212°F)"
 ->
Quality Judge: Passed (score: 0.95 >= 0.70)
 ->
Final Response: escalated = False, model_api_calls = 1, total_llm_api_calls = 1
```

### Scenario 2 — Quality Failure & Escalation
```text
User Prompt: "Write a complex distributed lock algorithm in Python with detailed edge cases."
 ->
Classifier Agent: task_type = coding, complexity = high (1 routing call)
 ->
Policy Selection: mistral-fast
 ->
Primary Execution: Responds with brief code snippet missing concurrency safety
 ->
Quality Judge: Failed (score: 0.52 < 0.70) -> Rejection reason: quality gate failed
 ->
Strong Model Escalation: Re-executes on mistral-strong (mistral-large-latest)
 ->
Final Response: escalated = True, model_api_calls = 2, total_llm_api_calls = 3
```

### Scenario 3 — Provider Failure & Failover
```text
User Prompt: "Summarize the history of quantum computing."
 ->
Policy Selection: groq-fast
 ->
Primary Execution: Groq returns HTTP 429 Rate Limit
 ->
Reliability Handler: Retries 2 times with backoff -> Still 429
 ->
Provider Failover: Automatically switches to mistral-fast
 ->
Execution Success: Responds via Mistral
 ->
Final Response: transport_fallback = True, model_used = mistral-fast
```
