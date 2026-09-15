# 🔀 Cost-Aware Multi-Model AI Router

> **Built a FastAPI-based intelligent LLM router that dynamically selects cost-efficient models based on request complexity, with cheap-first execution, failover, selective quality evaluation, escalation, and MongoDB-based cost/routing analytics.**

[![Next.js](https://img.shields.io/badge/Frontend-Next.js%2015-000000.svg?logo=next.js&logoColor=white)](https://nextjs.org/)
[![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![MongoDB](https://img.shields.io/badge/Database-MongoDB-47A248.svg?logo=mongodb&logoColor=white)](https://www.mongodb.com/)
[![Clerk](https://img.shields.io/badge/Auth-Clerk-6C47FF.svg?logo=clerk&logoColor=white)](https://clerk.com/)
[![Tailwind CSS](https://img.shields.io/badge/Styling-Tailwind%20CSS-38B2AC.svg?logo=tailwind-css&logoColor=white)](https://tailwindcss.com/)

---

## 🌐 Live Web Application

Experience the live cost-aware router dashboard and API:

- **Frontend Dashboard:** 👉 **[https://frontend-ten-hazel-32.vercel.app/](https://frontend-ten-hazel-32.vercel.app/)**
- **Backend API (Swagger):** 👉 **[https://ai-cost-aware-router-api.onrender.com/docs](https://ai-cost-aware-router-api.onrender.com/docs)**

---

## ❓ What it does ?

**Cost-Aware Multi-Model AI Router** is an intelligent LLM routing system that selects a cost-efficient model for each user request while maintaining response quality.

Instead of sending every request to an expensive model, the router follows a **cheap-first strategy**:

`User Request → Rules Engine → Classifier (when needed) → Cheapest Capable Model → Quality Check (selective) → Escalation/Fallback`

1. **Intelligent Cost-Aware Routing**: Uses a deterministic rules engine for obvious requests and an LLM classifier only when the request cannot be confidently classified by rules.
2. **Cheap-First Execution**: Attempts an inexpensive model before using stronger models, avoiding unnecessary calls to expensive models.
3. **Reliability & Failover**: Supports provider-level retries and failover. Handles temporary provider failures and rate limits.
4. **Selective Quality Evaluation**: Does not judge every response unnecessarily. Failed evaluations can trigger a single escalation to a stronger model with instructions for improvement.
5. **Cost & Performance Analytics**: Tracks per-request model cost, estimated savings, model usage, routing decisions, and API calls through MongoDB-backed APIs.
6. **MCP Model Registry**: Uses MCP-based tooling to retrieve provider pricing information and keep it synchronized.

---

## 💥 Problem Statement

AI applications often suffer from **cost inefficiencies** and **reliability issues**:
- **Overspending**: Sending every prompt to expensive, flagship models (like GPT-4 or Claude 3 Opus) wastes money on simple tasks like summarization or basic Q&A.
- **Complexity Misalignment**: Simple requests don't need deep reasoning, while complex requests fail on smaller, cheaper models.
- **Provider Outages**: Relying on a single LLM provider leads to downtime during outages or rate limits.
- **Silent Failures**: Cheap models may hallucinate or provide poor answers without a mechanism to evaluate and escalate to a better model.
- **Pricing Drift**: Model pricing changes frequently, making static cost configurations obsolete and inaccurate over time.

---

## 💡 Solution

**Cost-Aware Multi-Model AI Router** solves these issues by dynamically optimizing for both cost and quality:
- **Smart Routing**: Routes each request to the cheapest model capable of handling the task based on rules and LLM classification.
- **Robust Failover**: Automatically switches to another capable provider if the initial model fails or hits rate limits.
- **Automated Quality Control**: Selectively judges responses and escalates to a stronger model when the initial output is poor.
- **Transparent Analytics**: Provides a Next.js dashboard to monitor routing decisions, track costs, and calculate estimated savings compared to using a strong model by default.
- **MCP Integration**: Keeps pricing and registry information up to date without impacting the core request execution path.

### Which AI Models Are Used and Why?

The system groups models into two tiers: **Fast** (cheaper, quick response) and **Strong** (high quality, deep reasoning).

1. **Mistral (`mistral`)**:
   - *Fast*: `mistral-small-latest` (Great for fast chat, summarization)
   - *Strong*: `mistral-large-latest` (Excellent reasoning, coding, and multilingual support)
2. **Gemini (`gemini`)**:
   - *Fast*: `gemini-3.6-flash` (Cost-effective with a massive context window up to 1M tokens)
   - *Strong*: `gemini-3.6-flash` (Configured for more complex routing such as multimodal/vision processing and higher output token limits)
3. **Groq (`groq`)**:
   - *Fast*: `openai/gpt-oss-20b` (Ultra-fast inference for rapid classification and simple tasks)
   - *Strong*: `qwen/qwen3.6-27b` (Strong open-source reasoning capabilities served at blazing speeds)

---

## 🚀 How to Run it

### Prerequisites
- **Node.js 18+** & `npm`
- **Python 3.10+**
- Free API Keys:
  - **Gemini API Key**
  - **Groq API Key**
  - **Mistral API Key**
  - **MongoDB** (Local or Atlas) connection string
  - **Clerk** account for authentication
  - **LangSmith** API Key (Optional, for tracing)

---

### Step 1: Clone the Repository
```bash
git clone https://github.com/Suhasini30/ai-cost-aware-router.git
cd ai-cost-aware-router
```

---

### Step 2: Backend Setup & Execution
```bash
# Navigate to backend directory
cd backend

# Create and activate Python virtual environment
python -m venv venv
# On Windows (PowerShell):
.\venv\Scripts\activate
# On macOS / Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create your .env file
cp .env.example .env
```

*Fill in your keys in `backend/.env` (see the Environment Variables section below).*

```bash
# Start the FastAPI Backend Server
python server.py
# Or using uvicorn: uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```
*Backend runs locally at: `http://127.0.0.1:8000` (Swagger documentation at `http://127.0.0.1:8000/docs`)*

---

### Step 3: Frontend Setup & Execution
```bash
# Open a new terminal and navigate to frontend directory
cd frontend

# Install Node dependencies
npm install

# Create your local frontend environment file
cp .env.example .env
```

*Configure `frontend/.env` with the frontend variables listed below.*

```bash
# Start the Next.js Development Server
npm run dev
```
*Frontend runs locally at: `http://localhost:3000`*

---

## 🔑 What the ENV variables

Create your `.env` file in the backend directory and `.env` in the frontend directory.

### 1. Backend Environment Variables (`backend/.env`)

```env
# ==========================================
# 1. LLM Providers
# ==========================================
GEMINI_API_KEY=your_gemini_api_key_here
GROQ_API_KEY=your_groq_api_key_here
MISTRAL_API_KEY=your_mistral_api_key_here
XAI_API_KEY=your_xai_api_key_here

# ==========================================
# 2. Router Configuration
# ==========================================
CLASSIFIER_PROVIDER=groq
CLASSIFIER_MODEL=openai/gpt-oss-20b
JUDGE_PROVIDER=groq
JUDGE_MODEL=qwen/qwen3.6-27b

# ==========================================
# 3. Database (MongoDB)
# ==========================================
MONGO_DB_URL=mongodb+srv://user:password@cluster.mongodb.net/
MONGODB_URI=mongodb://localhost:27017
MONGODB_DATABASE=ai_cost_router
MONGODB_COLLECTION=requests

# ==========================================
# 4. Security & Tracing
# ==========================================
JWT_SECRET_KEY=your_jwt_secret_key
LANGCHAIN_API_KEY=your_langchain_api_key
LANGCHAIN_TRACING_V2=true
LANGCHAIN_PROJECT=cost-aware-router
LANGSMITH_API_KEY=your_langsmith_api_key

# ==========================================
# 5. Rules Engine Thresholds
# ==========================================
ROUTER_COMPLEXITY_LONG_PROMPT_CHARS=200
ROUTER_RULE_MAX_SIMPLE_QA_CHARS=80
ROUTER_JUDGE_MIN_ANSWER_CHARS=20
ROUTER_JUDGE_TASK_TYPES=coding,math,reasoning
ROUTER_HIGH_COMPLEXITY_KEYWORDS=complex,algorithm,architect,optimiz,distributed,concurren,production,critical
```

### 2. Frontend Environment Variables (`frontend/.env`)

```env
# ==========================================
# 1. API Connection
# ==========================================
NEXT_PUBLIC_API_URL=http://127.0.0.1:8000

# ==========================================
# 2. Clerk Authentication
# ==========================================
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_test_...
```

---

## 🔍 Router Details / Explainability

The router provides detailed information for each request so users can understand **why a model was selected, what happened during execution, and whether escalation was required**.

For every completed request, the dashboard can display relevant routing and evaluation information such as:

| Field                        | Description                                                          |
| ---------------------------- | -------------------------------------------------------------------- |
| **Initial Model**            | Model selected for the first execution attempt                       |
| **Final Model**              | Model that ultimately produced the final response                    |
| **Task Type**                | Classified task category, such as coding, reasoning, or general Q&A  |
| **Routing Confidence**       | Confidence associated with the routing/classification decision       |
| **Quality Score**            | Score produced when selective quality evaluation is performed        |
| **Initial Verdict**          | Quality evaluation result before any potential escalation            |
| **Escalated**                | Indicates whether the request was escalated to a stronger model      |
| **Rejection Reason**         | Reason the initial response was not accepted, when applicable        |
| **Issues Found**             | Problems identified during quality evaluation                        |
| **Improvement Instructions** | Guidance passed to the stronger model during escalation              |
| **Total Calls**              | Number of model/API calls involved in processing the request         |
| **Cost**                     | Estimated inference cost for the request                             |
| **Estimated Savings**        | Estimated savings compared with the configured strong-model baseline |

### Example Router Details

The following is an **illustrative example only** and does not represent a measured project result:

```text
┌─────────────────────────────────────┐
│          Router Details             │
├─────────────────────────────────────┤
│ Initial Model    : Fast Model       │
│ Task Type        : Coding           │
│ Routing Confidence: 0.91            │
│ Quality Score    : 45%              │
│ Initial Verdict  : Failed           │
│ Escalated        : Yes              │
│ Final Model      : Strong Model     │
│ Total Calls      : 2                │
│ Cost             : $0.00XX          │
│ Estimated Savings: $0.00XX          │
└─────────────────────────────────────┘
```

When a response is rejected by the quality evaluation, the Router Details view can also expose **why it was rejected**, including the identified issues and improvement instructions.

This makes the router more transparent than simply returning a final answer: users can inspect the **routing decision, model transition, quality evaluation, escalation, and cost** for an individual request.

---

## 📊 Evaluation

The router is evaluated against an always-strong-model baseline using a fixed set of test prompts covering simple Q&A, summarization, coding, reasoning, and other task types.

The evaluation measures:

- Routing accuracy
- Response quality
- Average cost per request
- Estimated cost savings
- Total LLM API calls
- Failover rate
- Escalation rate

Results are generated from the project's evaluation/test suite and are reported without hard-coded or manually estimated metrics.

---

## 🏗️ Architecture

```text
                         USER
                          │
                          ▼
                   ┌─────────────┐
                   │ Rules Engine│
                   └──────┬──────┘
                          │
                 Obvious request?
                    /           \
                  YES            NO
                   │              │
                   │        ┌─────▼─────┐
                   │        │ Classifier│
                   │        └─────┬─────┘
                   │              │
                   └──────┬───────┘
                          ▼
                 ┌─────────────────┐
                 │ Routing Policy  │
                 │ Cheap → Strong  │
                 └────────┬────────┘
                          ▼
                 ┌─────────────────┐
                 │ Model Execution │
                 └────────┬────────┘
                          │
             ┌────────────┴────────────┐
             │                         │
     Provider/API failure      Successful response
             │                         │
             ▼                         ▼
      Retry / Failover       Selective Quality Judge
                                  /         \
                               PASS         FAIL
                                │             │
                              FINAL       Escalation
                                              │
                                              ▼
                                         Strong Model
                                              │
             ┌────────────────────────────────┘
             ▼
          MongoDB
             │
             ▼
      Next.js Dashboard
```
