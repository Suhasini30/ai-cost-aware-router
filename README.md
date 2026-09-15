# 🔀 Cost-Aware Multi-Model AI Router

> **An intelligent multi-model LLM routing system that selects a cost-efficient model based on request complexity while maintaining response quality. The system combines deterministic routing, conditional classification, cheap-first execution, provider failover, selective quality evaluation, escalation, and MongoDB-based analytics.**

[![Next.js](https://img.shields.io/badge/Frontend-Next.js%2015-000000.svg?logo=next.js&logoColor=white)](https://nextjs.org/)
[![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![MongoDB](https://img.shields.io/badge/Database-MongoDB-47A248.svg?logo=mongodb&logoColor=white)](https://www.mongodb.com/)
[![Clerk](https://img.shields.io/badge/Auth-Clerk-6C47FF.svg?logo=clerk&logoColor=white)](https://clerk.com/)
[![Tailwind CSS](https://img.shields.io/badge/Styling-Tailwind%20CSS-38B2AC.svg?logo=tailwind-css&logoColor=white)](https://tailwindcss.com/)

---

## 🌐 Live Application

- **Frontend Dashboard:** 👉 **[https://frontend-ten-hazel-32.vercel.app/](https://frontend-ten-hazel-32.vercel.app/)**
- **Backend API:** 👉 **[https://ai-cost-aware-router-api.onrender.com/](https://ai-cost-aware-router-api.onrender.com/)**
- **Swagger API Documentation:** 👉 **[https://ai-cost-aware-router-api.onrender.com/docs](https://ai-cost-aware-router-api.onrender.com/docs)**

---

## ❓ What Does It Do?

The Cost-Aware Multi-Model AI Router is designed to solve a simple problem:

> **Why use an expensive model for every request when a cheaper model can handle many requests successfully?**

Instead of sending every prompt directly to a strong and expensive model, the router follows a **cheap-first strategy**:

```text
User Request
     │
     ▼
Rules Engine
     │
     ├── Obvious Request ─────────────┐
     │                                │
     └── Uncertain Request            │
                 │                    │
                 ▼                    │
             Classifier               │
                 │                    │
                 └─────────┬─────────┘
                           ▼
                    Routing Policy
                           │
                           ▼
                 Cheapest Capable Model
                           │
                           ▼
                    Model Execution
                           │
                 ┌──────────┴──────────┐
                 │                     │
              Success               Failure
                 │                     │
                 ▼                     ▼
          Selective Quality     Retry / Failover
                Judge
            ┌─────┴─────┐
           PASS       FAIL
            │           │
            ▼           ▼
          FINAL    Strong Model
                        │
                        ▼
                      FINAL
                        │
                        ▼
                     MongoDB
                        │
                        ▼
                Next.js Dashboard
```

The main objective is to reduce unnecessary inference cost without blindly sacrificing response quality.

---

## ✨ Key Highlights

- **Cost-Aware Routing** — selects models according to task requirements and configured cost/capability information.
- **Cheap-First Execution** — prefers an inexpensive capable model before moving to stronger models.
- **Rule-Based Routing** — avoids unnecessary LLM classification for requests that can be identified deterministically.
- **Conditional Classification** — uses an LLM classifier only when the rules engine cannot confidently determine the request type.
- **Multi-Provider Execution** — supports multiple LLM providers through provider-specific model adapters.
- **Retry & Failover** — handles provider failures and rate-limit-related failures without immediately exposing the failure to the user.
- **Selective Quality Evaluation** — evaluates responses only when configured conditions require judging.
- **Strong-Model Escalation** — a failed quality evaluation can trigger escalation to a stronger model.
- **Cost Tracking** — records model usage and estimated inference cost.
- **Routing Analytics** — tracks routing decisions, model usage, calls, cost, and savings information.
- **MongoDB History** — stores request and routing information for later analysis.
- **Explainable Routing** — exposes routing and evaluation details instead of returning only the final answer.
- **Clerk Authentication** — protects the application using Clerk-based authentication.
- **MCP-Based Registry Tooling** — supports retrieving provider/model pricing information separately from the normal request execution path.

---

## 💡 Problem Statement

Multi-model AI applications face several challenges when deciding which model should handle a request.

### 1. Overspending
Sending every request to a strong model increases inference cost even when the request is simple.
For example: *"What is the capital of India?"* does not necessarily require the same model capability as: *"Design a distributed event-driven architecture for a high-throughput financial transaction system."*

### 2. Complexity Misalignment
A cheap model may be sufficient for simple requests but may struggle with complex coding, reasoning, or architectural tasks.

### 3. Provider Reliability
A model provider can experience rate limits, temporary API failures, service interruptions, or model availability issues. A router relying on only one provider becomes a single point of failure.

### 4. Silent Quality Problems
A model can successfully return an HTTP response while still producing a poor answer. Therefore: **API Success ≠ Answer Quality**. The router addresses this through selective quality evaluation.

### 5. Pricing Drift
LLM provider pricing can change over time. A static model registry can therefore become outdated. The project includes separate registry/pricing tooling to help identify provider pricing information without putting an MCP call on every user request.

---

## 🧠 Solution

The router combines cost, capability, reliability, and quality control. The important design principle is:
**Use the cheapest model that is capable of handling the request, rather than always using the strongest model.**

---

## 🏗️ Architecture

```text
                ┌───────────────┐
                │     USER      │
                └───────┬───────┘
                        │
                        ▼
                ┌──────────────────┐
                │   Rules Engine   │
                └────────┬─────────┘
                         │
         ┌───────────────┴───────────────┐
         │                               │
  Obvious Request                Uncertain Request
         │                               │
         ▼                               │
 ┌──────────────┐                        │
 │  Classifier  │                        │
 └──────┬───────┘                        │
        │                                │
        └───────────────┬────────────────┘
                        ▼
                ┌─────────────────────┐
                │   Routing Policy    │
                │   Cheap → Strong    │
                └──────────┬──────────┘
                           │
                           ▼
                ┌─────────────────────┐
                │  Cheapest Capable   │
                │        Model        │
                └──────────┬──────────┘
                           │
                           ▼
                ┌─────────────────────┐
                │   Model Execution   │
                └──────────┬──────────┘
                           │
              ┌────────────┴────────────┐
              │                         │
           SUCCESS                   FAILURE
              │                         │
              │                  Retry / Failover
              │                         │
              ▼                         ▼
      ┌─────────────────┐       Another Provider
      │ Selective Judge │
      └───────┬─────────┘
              │
        ┌─────┴─────┐
        │           │
      PASS         FAIL
        │           │
        ▼           ▼
      FINAL    Strong Model
                    │
                    ▼
                  FINAL
                    │
                    ▼
            ┌───────────┐
            │  MongoDB  │
            └─────┬─────┘
                  │
                  ▼
            ┌───────────────┐
            │  Next.js UI   │
            │   Dashboard   │
            └───────────────┘
```

---

## ⚙️ How It Works

### 1. User Request
The user submits a natural-language prompt through the web application.

### 2. Rules Engine
The router first checks whether the request can be classified using deterministic rules. This avoids unnecessary LLM calls for simple requests. Routing signals include prompt length, simple-question patterns, task type, complexity keywords, and configured thresholds.

### 3. Conditional Classification
If deterministic rules cannot confidently determine the request requirements, the router uses an LLM classifier to extract routing information (task type, complexity, capabilities, routing confidence).

### 4. Routing Policy
The routing policy uses the available model information to select a suitable model. The general principle is **Cheapest capable model → Stronger model only when required**.

### 5. Model Execution
The selected provider adapter executes the request. The system supports multiple providers, allowing the router to select or fall back to another provider when necessary.

### 6. Provider Failure
If a provider fails because of an API/provider problem, the reliability layer can **Retry / Failover** to an alternative configured model/provider.

### 7. Selective Quality Evaluation
When judging is required, an independent strong model evaluates the generated response. The judge produces quality information (score, verdict, issues, instructions).

### 8. Quality Failure and Escalation
If the generated answer fails the quality evaluation, the router can escalate the request to a stronger model using the improvement instructions.

---

## 🔍 Router Details / Explainability

One of the important features of the project is that the user can inspect what happened during an individual request.

| Field | Description |
| --- | --- |
| **Initial Model** | Model selected for the first execution |
| **Final Model** | Model that generated the final response |
| **Task Type** | Detected/classified task |
| **Routing Confidence** | Confidence associated with the routing decision |
| **Quality Score** | Score from the quality evaluator when judging occurs |
| **Verdict** | Quality evaluation result |
| **Escalated** | Whether the request required escalation |
| **Rejection Reason** | Why the initial answer was rejected |
| **Issues Found** | Problems identified by the evaluator |
| **Improvement Instructions** | Guidance provided for escalation |
| **Total Calls** | Model/API calls used during processing |
| **Cost** | Estimated request cost |
| **Estimated Savings** | Estimated savings against the configured strong-model baseline |

### Example

*The following is an illustrative example only.*

```text
┌──────────────────────────────────────┐
│           Router Details             │
├──────────────────────────────────────┤
│ Initial Model      : Fast Model      │
│ Final Model        : Strong Model    │
│ Task Type          : Coding          │
│ Routing Confidence : 0.91            │
│ Quality Score      : 90%             │
│ Verdict            : Failed → Retry  │
│ Escalated          : Yes             │
│ Total Calls        : 2               │
│ Cost               : $0.00XX         │
│ Estimated Savings  : $0.00XX         │
└──────────────────────────────────────┘
```

The distinction between routing confidence and quality score is intentional:
- **Routing Confidence:** "How confident was the router in its model selection?"
- **Quality Score:** "How good was the generated answer?"

---

## 🚀 Installation

### Prerequisites
- Python 3.10+
- Node.js 18+ & npm
- MongoDB connection string
- API keys for LLM providers (Gemini, Groq, Mistral, xAI)
- Clerk credentials for authentication

### 1️⃣ Clone the Repository
```bash
git clone https://github.com/Suhasini30/ai-cost-aware-router.git
cd ai-cost-aware-router
```

### 2️⃣ Backend Setup
```bash
cd backend
python -m venv venv

# Windows PowerShell:
.\venv\Scripts\Activate.ps1
# macOS / Linux:
source venv/bin/activate

pip install -r requirements.txt
cp .env.example .env

# Start the server:
python server.py
# Or using uvicorn directly: uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```
- Backend runs at: `http://127.0.0.1:8000`
- Swagger Docs: `http://127.0.0.1:8000/docs`

### 3️⃣ Frontend Setup
```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```
- Frontend runs at: `http://localhost:3000`

---

## 🔑 Environment Variables

Use `.env.example` as the source of truth. Example variables include:

### Backend
```env
# Provider Config
GEMINI_API_KEY=your_gemini_api_key
GROQ_API_KEY=your_groq_api_key
MISTRAL_API_KEY=your_mistral_api_key
XAI_API_KEY=your_xai_api_key

# Router Configuration
CLASSIFIER_PROVIDER=groq
CLASSIFIER_MODEL=your_classifier_model
JUDGE_PROVIDER=groq
JUDGE_MODEL=your_judge_model

# MongoDB Configuration
MONGO_DB_URL=your_mongodb_connection_string
MONGODB_URI=your_mongodb_uri
MONGODB_DATABASE=your_database
MONGODB_COLLECTION=your_collection
```

---

## 🔗 Links
- **GitHub Repository:** [https://github.com/Suhasini30/ai-cost-aware-router](https://github.com/Suhasini30/ai-cost-aware-router)
- **Live Frontend:** [https://frontend-ten-hazel-32.vercel.app/](https://frontend-ten-hazel-32.vercel.app/)
- **Backend API:** [https://ai-cost-aware-router-api.onrender.com/](https://ai-cost-aware-router-api.onrender.com/)
- **Swagger Documentation:** [https://ai-cost-aware-router-api.onrender.com/docs](https://ai-cost-aware-router-api.onrender.com/docs)

---

## ⭐ Key Takeaway

> **Don't send every request to the most expensive model. Route each request to the cheapest model that can handle it, verify quality when necessary, and escalate only when required.**
