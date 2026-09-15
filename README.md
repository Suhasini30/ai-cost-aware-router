# 🔀 Cost-Aware Multi-Model AI Router

> **An intelligent multi-model LLM routing system that selects a cost-efficient model based on request complexity while maintaining response quality. Combining deterministic rule routing, LLM classification, cheap-first execution, provider failover, selective quality judging, escalation, and MongoDB analytics.**

[![Next.js](https://img.shields.io/badge/Frontend-Next.js%2015-000000.svg?logo=next.js&logoColor=white)](https://nextjs.org/)
[![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![MongoDB](https://img.shields.io/badge/Database-MongoDB-47A248.svg?logo=mongodb&logoColor=white)](https://www.mongodb.com/)
[![Clerk](https://img.shields.io/badge/Auth-Clerk-6C47FF.svg?logo=clerk&logoColor=white)](https://clerk.com/)
[![Tailwind CSS](https://img.shields.io/badge/Styling-Tailwind%20CSS-38B2AC.svg?logo=tailwind-css&logoColor=white)](https://tailwindcss.com/)

---

## 🌐 Live Web Application

Experience the live Cost-Aware AI Router:
👉 **[https://frontend-ten-hazel-32.vercel.app/](https://frontend-ten-hazel-32.vercel.app/)**

---

## ❓ What it does ?

The **Cost-Aware Multi-Model AI Router** is an interactive, intelligent multi-model routing system that puts LLM user requests through an automated cost and quality optimization pipeline:

* **Intake User Prompt:** Users enter natural-language prompts via an interactive Next.js console or API endpoints (`POST /router/ask`).
* **Deterministic Rules Engine:** Instantly evaluates simple QA prompts and short requests using regex/length heuristics (`rules/local`), bypassing LLM classification with 0 API calls and zero classification latency.
* **LLM Classifier Agent:** When rules are inconclusive, a lightweight classifier assesses task type (`general_qa`, `code_generation`, `complex_reasoning`, etc.), complexity (`low`, `medium`, `high`), required capability, and confidence rating.
* **Cost-Aware Routing Policy:** Queries the model registry and selects the cheapest capable model (`FAST` vs `STRONG` tier) meeting capability requirements.
* **Multi-Provider Execution:** Executes inference across multiple providers (Groq, Mistral, Gemini, xAI, OpenAI) via unified provider adapters.
* **Provider Retry & Failover:** Catches provider rate limits (429) or server outages (5xx) with automatic exponential backoff retries and fallback to alternative capable providers.
* **Selective Quality Evaluation:** Evaluates generated response text against heuristic quality benchmarks (`quality_pass_threshold = 0.70`).
* **Single-Pass Strong Model Escalation:** If the initial response fails quality evaluation, the system automatically escalates the query to a stronger model (e.g. `mistral-strong` / `groq-strong`) while enforcing a strict single-escalation limit.
* **Cost & Savings Calculation:** Computes exact input/output token costs (`actual_cost`) and compares them against the baseline cost (`baseline_cost` of using the strongest model directly), rendering dollar and percentage savings.
* **MongoDB Persistence & History:** Asynchronously records full execution logs, trace stages, token counts, latency, and quality scores in MongoDB (`query_logs`) via background tasks.
* **LangSmith Observability:** Traces pipeline spans (`@traceable`) for end-to-end cloud latency and token observability.
* **MCP Pricing Registry Tooling:** Includes an out-of-band pricing audit tool (`scripts/check_model_registry.py`) calling Parallel Search MCP (`https://search.parallel.ai/mcp`) to detect provider price drift into `registry_drift_report.json`.

---

## 💥 Problem Statement

Multi-model AI applications face severe cost and reliability challenges when deciding which model should handle a user query:

* **Overspending on Expensive Models:** Sending simple queries like *"What is the boiling point of water?"* to state-of-the-art models (GPT-4o, Claude 3.5 Sonnet) wastes significant inference budget.
* **Complexity Misalignment:** Inexpensive models can fail on complex coding, mathematical proof, or architectural reasoning if selected blindly without capability matching.
* **Provider Single Point of Failure:** Relying on a single model provider exposes applications to rate-limiting (429) or API outages.
* **Silent Quality Failures:** An HTTP 200 response from an LLM does not guarantee answer quality. Poor or incomplete answers reach users unless evaluated.
* **Pricing Drift:** LLM provider pricing changes frequently over time, rendering static registry pricing outdated.

---

## 💡 Solution

The Cost-Aware Multi-Model AI Router eliminates wasteful AI spending through an automated multi-tier architecture:

* **Cheap-First Execution:** Prefers inexpensive capable models before escalating to stronger models.
* **Zero Classification Overhead:** Rule engine handles simple QA deterministically with zero classifier calls.
* **Empirical Quality Gate:** Evaluates answer quality and escalates to strong models only when quality falls below threshold.
* **Automated Retries & Provider Failover:** Reliability layer prevents provider rate limits or outages from breaking user queries.
* **Transparent Explainable Routing:** Renders full stage-by-step trace timelines, model metadata, token metrics, and cost savings.

---

## 🚀 How to Run it

### Prerequisites
* Node.js 18+ & npm
* Python 3.10+
* API Keys for LLM Providers (Groq, Mistral, Gemini)
* MongoDB Atlas connection string
* Clerk account (for user authentication)
* LangSmith API Key *(optional for tracing)*

### Step 1: Clone the Repository
```bash
git clone https://github.com/Suhasini30/ai-cost-aware-router.git
cd ai-cost-aware-router
```

### Step 2: Backend Setup & Execution
```bash
# Navigate to backend directory
cd backend

# Create and activate Python virtual environment
python -m venv venv

# On Windows (PowerShell):
.\venv\Scripts\Activate.ps1
# On macOS / Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create your .env file from example
cp .env.example .env
```
Fill in your keys in `backend/.env` (see the Environment Variables section below).

```bash
# Start the FastAPI Backend Server
python server.py
# Or using uvicorn directly:
# uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```
Backend runs locally at: `http://127.0.0.1:8000` (Swagger documentation at `http://127.0.0.1:8000/docs`)

### Step 3: Frontend Setup & Execution
```bash
# Open a new terminal and navigate to frontend directory
cd frontend

# Install Node dependencies
npm install

# Create your local frontend environment file
cp .env.example .env.local
```
Configure `frontend/.env.local` with the frontend variables listed below.

```bash
# Start the Next.js Development Server
npm run dev
```
Frontend runs locally at: `http://localhost:3000`

---

## 🔑 What the ENV variables

Create your `.env` file in the `backend/` directory and `.env.local` in the `frontend/` directory.

### 1. Root & Backend Environment Variables (`backend/.env`)

```env
# ==========================================
# 1. LLM Provider API Keys
# ==========================================
GEMINI_API_KEY=your_gemini_api_key_here
GROQ_API_KEY=gsk_your_groq_api_key_here
MISTRAL_API_KEY=your_mistral_api_key_here
XAI_API_KEY=your_xai_api_key_here

# ==========================================
# 2. Router & Classifier Settings
# ==========================================
CLASSIFIER_PROVIDER=groq
CLASSIFIER_MODEL=openai/gpt-oss-20b
JUDGE_PROVIDER=groq
JUDGE_MODEL=qwen/qwen3.6-27b

# ==========================================
# 3. LangSmith Tracing & Observability
# ==========================================
LANGCHAIN_API_KEY=lsv2_pt_your_langchain_api_key_here
LANGCHAIN_TRACING_V2=true
LANGCHAIN_PROJECT=cost-aware-router
LANGSMITH_API_KEY=lsv2_pt_your_langsmith_api_key_here

# ==========================================
# 4. Security & JWT Token Sessions
# ==========================================
JWT_SECRET_KEY=your_generated_jwt_secret_key_here
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# ==========================================
# 5. Production MongoDB Database
# ==========================================
MONGO_DB_URL=mongodb+srv://user:password@cluster.mongodb.net/
MONGODB_URI=mongodb://localhost:27017
MONGODB_DATABASE=ai_cost_router
MONGODB_COLLECTION=query_logs

# ==========================================
# 6. Clerk Authentication (Backend JWKS Verification)
# ==========================================
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_test_your_clerk_publishable_key
CLERK_SECRET_KEY=sk_test_your_clerk_secret_key
CLERK_ISSUER=https://your-clerk-domain.clerk.accounts.dev
CLERK_JWKS_URL=https://your-clerk-domain.clerk.accounts.dev/.well-known/jwks.json

# ==========================================
# 7. Router Rule Engine Parameters
# ==========================================
ROUTER_COMPLEXITY_LONG_PROMPT_CHARS=200
ROUTER_RULE_MAX_SIMPLE_QA_CHARS=80
ROUTER_JUDGE_MIN_ANSWER_CHARS=20
ROUTER_JUDGE_TASK_TYPES=coding,math,reasoning
ROUTER_HIGH_COMPLEXITY_KEYWORDS=complex,algorithm,architect,optimiz,distributed,concurren,production,critical
```

### 2. Frontend Environment Variables (`frontend/.env.local`)

```env
# ==========================================
# Frontend API URL & Deployments
# ==========================================
# Point to local FastAPI backend for development
NEXT_PUBLIC_API_URL=http://127.0.0.1:8000

# ==========================================
# Clerk Authentication Keys (Frontend)
# ==========================================
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_test_your_clerk_publishable_key
```

---

## 🏗️ Architecture

```mermaid
flowchart TD
    User["1. User Prompt"] --> Frontend["2. Next.js 15 Console UI"]
    Frontend -->|"Get Session Token"| Clerk["3. Clerk Auth Service"]
    Clerk -->|"Return Session Token"| Frontend
    Frontend -->|"POST /router/ask + Authorization Bearer"| FastAPI["4. FastAPI Backend Gateway"]
    
    FastAPI --> AuthDep["5. Auth Dependency: get_current_user_id"]
    AuthDep -->|"RS256 JWKS Signature Verification"| ClerkJWKS["6. Clerk JWKS Endpoint / Cache"]
    
    AuthDep --> PipelineRoot["7. Router Pipeline: answer_prompt"]
    
    subgraph RouterPipeline ["Routing & Execution Pipeline"]
        PipelineRoot --> RuleEngine{"8. Deterministic Rule Engine"}
        RuleEngine -->|"Obvious QA / Short Prompt"| Policy["10. Routing Policy"]
        RuleEngine -->|"Uncertain Request"| ClassifierAgent["9. LLM Classifier Agent"]
        ClassifierAgent -->|"Task Type & Complexity"| Policy
        
        Policy --> ModelRegistry[("Model Registry")]
        Policy -->|"Selected Model"| PrimaryExec["11. Primary Model Execution"]
        
        PrimaryExec -->|"Transport Error 429 / 5xx"| Failover["12. Retry & Provider Failover"]
        Failover --> PrimaryExec
        
        PrimaryExec -->|"Answer Text"| Judge{"13. Selective Quality Judge"}
        
        Judge -->|"Pass: score >= 0.70"| FinalResp["14. Construct AskResponse"]
        Judge -->|"Fail: score < 0.70"| StrongEscalation["13b. Strong Model Escalation Pass"]
        StrongEscalation --> FinalResp
    end
    
    FinalResp -->|"Background Async Task"| Mongo[("15. MongoDB: query_logs")]
    FinalResp -->|"Telemetry Spans"| LangSmith["16. LangSmith Tracing"]
    FinalResp -->|"Return AskResponse JSON"| Frontend
    Frontend --> UserRender["17. Render Answer, Cost & Trace Timeline"]
```

---

## 🛠️ Step by Step Implementation Journey

Here is the complete chronological journey of designing, constructing, hardening, and deploying the Cost-Aware Multi-Model AI Router:

### Phase 1: Architectural Blueprint & Schema Modeling
* Defined strongly-typed Pydantic schemas for classification decisions (`ClassifyRequest`/`Response`), route parameters (`RouteRequest`/`Response`), and pipeline outputs (`AskRequest`/`AskResponse`).
* Designed execution trace stage structures (`RouteStage`) to expose internal router decisions transparently to clients.
* Built modular FastAPI application structure with async lifespan managers, dependency injection, and health status routes.

### Phase 2: Static Model Registry & Provider Adapters
* Built static model registry (`app/models/registry.py`) storing model specs (`ModelSpec`), input/output pricing per 1K tokens, context windows, and capability tags for Groq, Mistral, and Gemini.
* Engineered unified provider execution interface (`app/execution/base.py`, `service.py`) supporting Groq, Mistral, Gemini, xAI, and OpenAI adapters.

### Phase 3: Deterministic Rule Engine & LLM Classifier Agent
* Built low-latency rule engine (`rules/local`) using prompt length heuristics and regex patterns to classify simple QA requests with 0 LLM calls.
* Built LLM classifier agent (`app/router/agent.py`) using `mistral-large-latest` (or configured provider) to assess task type, complexity (`low`, `medium`, `high`), and confidence score for ambiguous requests.

### Phase 4: Cost-Aware Policy & Price Breakdown Engine
* Developed routing policy (`app/router/policy.py`) to query capability tags, filter active models by confidence threshold, and select the cheapest capable model.
* Engineered token cost calculator (`app/cost/calculator.py`) computing actual cost vs baseline cost (cost if strongest model was used directly) and dollar/percentage savings.

### Phase 5: Provider Failover & Reliability Layer
* Created reliability engine (`app/reliability/`) handling network timeouts, HTTP 429 rate limits, and 5xx provider outages.
* Implemented exponential backoff retries and automatic failover to alternative capable model providers.

### Phase 6: Selective Quality Judge & Single-Pass Escalation Gate
* Built quality evaluator (`app/eval/evaluator.py`) assessing answer structure, completeness, and score against `quality_pass_threshold = 0.70`.
* Enforced a strict single-escalation pipeline invariant: if quality score fails, the query escalates to `strongest_capable` model, but never loops infinitely.

### Phase 7: MongoDB Persistence & History Service
* Connected Motor async MongoDB manager (`app/db/mongo.py`) with collection index setup (`idx_unique_request_id`, `idx_user_created`, `idx_created_at`, `idx_final_model`, `idx_passed`).
* Scheduled non-blocking background persistence (`persist_ask_response`) via FastAPI `BackgroundTasks`.

### Phase 8: Modern Next.js Interactive Console & Analytics Dashboard
* Built Next.js 15 App Router frontend featuring prompt submission console (`/console`), interactive stage trace timeline (`TraceTimeline`), cost breakdown cards (`CostCard`), and summary metrics.
* Developed Analytics dashboard (`/analytics`) rendering call volume, cost savings, model distribution, and escalation charts.

### Phase 9: Clerk Authentication & Security Layer
* Integrated Clerk Authentication across frontend components (`<ClerkProvider>`, `useAuth()`, `getToken()`) and Next.js route middleware.
* Built backend RS256 JWKS token verification (`app/auth/clerk.py`) with key caching to secure `/router/ask` and history endpoints.

### Phase 10: LangSmith Observability & Tracing Integration
* Integrated LangSmith SDK with `@traceable` wrappers across `answer_prompt`, `classify_prompt`, `execute`, and `evaluate_answer`.
* Enforced strict API key separation guarantees (`LANGCHAIN_API_KEY` for telemetry only; classifier agent never receives tracing key).

### Phase 11: MCP Pricing Audit Tooling & Production Deployment
* Built out-of-band pricing audit script (`scripts/check_model_registry.py`) connecting to Parallel Search MCP (`https://search.parallel.ai/mcp`) via JSON-RPC to inspect model price drift into `registry_drift_report.json`.
* Hardened production deployment configurations for Render (backend) and Vercel (frontend).

---

## 🧪 Testing

### Run Backend Test Suites:
```bash
# In backend directory with virtualenv active:
pytest tests/ -v
```

### Run Frontend Production Build Verification:
```bash
# In frontend directory:
npm run build
```

---

## 📚 Deep-Dive Technical Documentation

For in-depth specifications, architectural diagrams, and flowcharts, explore the dedicated documentation guides:

| Document | Description |
| :--- | :--- |
| **[System Architecture](docs/architecture.md)** | Technical stack, component topology, backend/frontend modules, and MongoDB schema |
| **[Workflow Mechanics](docs/workflow.md)** | End-to-end execution flowchart, request types, failover, and cost tracking formulas |
| **[Clerk Authentication](docs/clerk.md)** | Clerk setup guide, RS256 JWKS token verification, environment config, and troubleshooting |
| **[Render Deployment Guide](docs/render.md)** | Step-by-step Render backend deployment, MongoDB Atlas integration, CORS, and env variables |
| **[User Query Workflow](docs/user-query-workflow.md)** | Detailed lifecycle of a user prompt from input submit to UI console card rendering |
| **[LangSmith Observability](docs/langsmith.md)** | LangSmith setup, `@traceable` span architecture, privacy controls, and cloud tracing |

---

## ⭐ Key Takeaway

> **Don't send every request to the most expensive model. Route each request to the cheapest model that can handle it, verify quality when necessary, and escalate only when required.**
