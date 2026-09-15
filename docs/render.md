# Render Deployment Guide

> **Step-by-Step Backend Deployment to Render**

---

## 1. Prerequisites

Before deploying the backend to Render, ensure you have:
* A GitHub repository containing the project code.
* A [Render](https://render.com/) account.
* A MongoDB database instance (e.g., [MongoDB Atlas](https://www.mongodb.com/cloud/atlas)).
* API keys for configured LLM providers (Groq, Mistral, Gemini).
* Clerk project credentials (`CLERK_ISSUER`, `CLERK_JWKS_URL`).

---

## 2. Step 1 — Push Repository to GitHub

Ensure your workspace structure matches the repository layout:

```text
multi_ai/
├── backend/
│   ├── app/
│   ├── requirements.txt
│   ├── server.py
│   └── .env.example
├── frontend/
└── README.md
```

---

## 3. Step 2 — Create Render Web Service

1. Log into the **Render Dashboard** (`dashboard.render.com`).
2. Click **New +** $\rightarrow$ **Web Service**.
3. Connect your **GitHub** account and select the `multi_ai` repository.
4. Configure the Web Service settings:
   * **Name:** `cost-aware-router-api`
   * **Region:** Select the closest region (e.g., Oregon, Frankfurt, Singapore).
   * **Branch:** `main` (or default branch).
   * **Root Directory:** `backend` *(CRITICAL: Must be set to `backend`)*
   * **Runtime:** `Python 3`
   * **Build Command:** `pip install -r requirements.txt`
   * **Start Command:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`

---

## 4. Step 3 — Environment Variables Checklist

Configure the following environment variables in the Render Web Service **Environment** section (derived directly from `backend/.env.example`):

| Variable Name | Purpose | Required | Example / Default |
| :--- | :--- | :--- | :--- |
| `GROQ_API_KEY` | Groq LLM inference key | Yes | `gsk_...` |
| `MISTRAL_API_KEY` | Mistral LLM inference key | Yes | `your_mistral_key` |
| `GEMINI_API_KEY` | Google Gemini LLM key | Yes | `AIzaSy...` |
| `XAI_API_KEY` | xAI API key (if used) | No | `xai-...` |
| `CLASSIFIER_PROVIDER` | Default classifier provider | Yes | `groq` |
| `CLASSIFIER_MODEL` | Default classifier model API ID | Yes | `openai/gpt-oss-20b` |
| `JUDGE_PROVIDER` | Quality judge provider | Yes | `groq` |
| `JUDGE_MODEL` | Quality judge model API ID | Yes | `qwen/qwen3.6-27b` |
| `MONGODB_URI` | MongoDB Atlas connection string | Yes | `mongodb+srv://user:pass@cluster.mongodb.net/` |
| `MONGODB_DATABASE` | Database name | Yes | `ai_cost_router` |
| `CLERK_ISSUER` | Clerk Issuer domain | Yes | `https://clerk.<id>.clerk.accounts.dev` |
| `CLERK_JWKS_URL` | Clerk JWKS public key URL | Yes | `https://clerk.<id>.clerk.accounts.dev/.well-known/jwks.json` |
| `LANGCHAIN_API_KEY` | LangSmith tracing key | No | `lsv2_pt_...` |
| `LANGCHAIN_TRACING_V2` | Enable LangSmith tracing | No | `true` |
| `LANGCHAIN_PROJECT` | LangSmith project name | No | `cost-aware-router` |
| `JWT_SECRET_KEY` | Local JWT secret key | Yes | `your_generated_secret_key` |

---

## 5. Step 4 — MongoDB Atlas Setup

1. Create a MongoDB cluster on MongoDB Atlas.
2. Under **Database Access**, create a user with read/write privileges.
3. Under **Network Access**, click **Add IP Address** and select **Allow Access from Anywhere** (`0.0.0.0/0`) so Render instances can connect.
4. Copy the connection string into Render's `MONGODB_URI` variable:
   `mongodb+srv://<username>:<password>@cluster.mongodb.net/ai_cost_router?retryWrites=true&w=majority`

---

## 6. Step 5 — CORS Configuration

In `backend/app/core/config.py`, the backend allowed origins list (`frontend_origins`) includes:
* `http://localhost:3000`
* `https://frontend-ten-hazel-32.vercel.app`

Ensure your deployed frontend URL is included in `frontend_origins` so browsers permit cross-origin requests.

---

## 7. Step 6 — Frontend Connection Configuration

On your Vercel (or production frontend host) environment settings, set the backend API URL:

```env
NEXT_PUBLIC_API_URL=https://cost-aware-router-api.onrender.com
```

---

## 8. Step 7 — Clerk Production Alignment

Ensure the Clerk issuer configured on Render matches the production Clerk instance issuer:

```env
CLERK_ISSUER=https://clerk.<your-id>.clerk.accounts.dev
CLERK_JWKS_URL=https://clerk.<your-id>.clerk.accounts.dev/.well-known/jwks.json
```

---

## 9. Step 8 — Deployment Verification Checklist

- [ ] Render build step (`pip install -r requirements.txt`) completes successfully.
- [ ] Web service starts without errors on `$PORT`.
- [ ] `GET https://cost-aware-router-api.onrender.com/health` returns `{"status": "healthy"}`.
- [ ] MongoDB connection succeeds during startup lifespan.
- [ ] `GET https://cost-aware-router-api.onrender.com/models` returns model registry JSON.
- [ ] Frontend can successfully execute `POST /router/ask` with a Clerk Bearer token.
- [ ] Query history documents appear in MongoDB `query_logs` collection.

---

## 10. Common Render Errors & Fixes

* **Build Failed (`ModuleNotFoundError`):** Ensure **Root Directory** is set to `backend`.
* **Port Binding Error (`Address already in use` or startup timeout):** Ensure Start Command uses `--port $PORT` instead of a hardcoded port.
* **MongoDB Connection Timeout:** Ensure MongoDB Atlas Network Access permits `0.0.0.0/0`.
* **500 Internal Server Error on `/router/ask`:** Verify provider API keys (`GROQ_API_KEY`, `MISTRAL_API_KEY`) are non-empty and active on Render.
