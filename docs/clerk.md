# Clerk Authentication Guide & Setup

> **Cost-Aware Multi-Model AI Router**

---

## 1. What Clerk Does

**Clerk** (`@clerk/nextjs` v6) provides user management, authentication UI, and JWT token issuance for the application.

* **Frontend:** Handles user sign-in (`<SignInButton />`), sign-up (`<SignUpButton />`), and session management (`<UserButton />`, `useAuth()`). Provides short-lived session tokens via `getToken()`.
* **Backend:** Protects API endpoints (`POST /router/ask`, `GET /history`, `GET /analytics`) by verifying RS256 JWT signatures against Clerk's JSON Web Key Set (JWKS) public keys.

---

## 2. Step-by-Step Clerk Application Setup

1. **Sign Up / Sign In:** Go to [clerk.com](https://clerk.com/) and log into the Clerk Dashboard.
2. **Create Application:** Click **+ Add application**, name it (e.g., `Cost-Aware Router`), and select desired sign-in strategies (Email, Google, GitHub, etc.).
3. **Copy API Keys:** Navigate to **API Keys** in the sidebar. Copy:
   * **Publishable key** (`pk_test_...` or `pk_live_...`)
   * **Secret key** (`sk_test_...` or `sk_live_...`)
4. **Copy Issuer Domain:** Under **API Keys** or **JWKS URL**, identify your Clerk Issuer URL (e.g., `https://clerk.<your-id>.clerk.accounts.dev`).

---

## 3. Environment Variables

### Backend Variables (`backend/.env`)

```env
# Clerk Secret Key (for Clerk SDK administrative calls if required)
CLERK_SECRET_KEY=sk_test_...

# Clerk Publishable Key (mirrored for backend reference if needed)
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_test_...

# Clerk Issuer URL (used by PyJWT to verify 'iss' claim)
CLERK_ISSUER=https://clerk.<your-id>.clerk.accounts.dev

# Clerk Public JWKS URL (used by httpx to fetch RS256 public keys)
CLERK_JWKS_URL=https://clerk.<your-id>.clerk.accounts.dev/.well-known/jwks.json

# JWKS key cache TTL in seconds (default: 600s)
CLERK_JWKS_CACHE_TTL_S=600
```

### Frontend Variables (`frontend/.env.local`)

```env
# Public backend API URL
NEXT_PUBLIC_API_URL=http://127.0.0.1:8000

# Clerk Publishable Key (required by @clerk/nextjs)
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_test_...
```

---

## 4. Local Development Flow

```text
User → Frontend UI → Clerk React SDK (getToken) → Header: Authorization: Bearer <jwt> → FastAPI Backend (get_current_user_id) → RS256 JWKS Verification → user_id
```

1. Next.js wraps the app in `<ClerkProvider>` (`app/layout.tsx`).
2. When submitting a prompt, `ConsolePage` calls `await getToken()`.
3. The API client attaches the token as `Authorization: Bearer <jwt>`.
4. FastAPI dependency `get_current_user_id` (`app/auth/dependencies.py`) decodes the token header to locate the Key ID (`kid`), fetches keys from `CLERK_JWKS_URL`, verifies the RS256 signature, validates `exp` and `iss` claims, and extracts `sub` as `user_id`.

---

## 5. Production Configuration (Render + Vercel)

When deploying Frontend to Vercel and Backend to Render:

1. **Allowed Origins (`frontend_origins`):** Ensure the Render backend's `FRONTEND_ORIGINS` setting includes your production Vercel URL:
   `https://frontend-ten-hazel-32.vercel.app`
2. **Clerk Production Domain:** In Clerk Dashboard, add your Vercel production domain under **Production Instance** or **Allowed Origins**.
3. **Backend Env on Render:** Set `CLERK_ISSUER` and `CLERK_JWKS_URL` in the Render Web Service Environment settings.

---

## 6. Common Troubleshooting & Problems

* **`401 Unauthorized - authentication is not configured`:**
  * **Cause:** `CLERK_JWKS_URL` or `CLERK_ISSUER` is empty in `backend/.env`.
  * **Fix:** Ensure both variables are non-empty and accurately configured in `.env`.
* **`401 Unauthorized - token expired`:**
  * **Cause:** The Clerk session token expired prior to request execution.
  * **Fix:** Ensure `getToken()` is called dynamically before sending API requests rather than storing tokens in static variables.
* **`401 Unauthorized - token issuer mismatch`:**
  * **Cause:** `CLERK_ISSUER` in `backend/.env` does not match the `iss` claim inside the token (e.g. trailing slash discrepancies).
  * **Fix:** Ensure `CLERK_ISSUER` matches the exact issuer string issued by Clerk.
* **CORS Error in Browser:**
  * **Cause:** The frontend domain is not listed in `settings.frontend_origins`.
  * **Fix:** Update `frontend_origins` in `app/core/config.py` or `.env`.
