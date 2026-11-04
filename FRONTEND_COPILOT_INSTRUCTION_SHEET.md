# Frontend Copilot Instruction Sheet (Backend-Aligned)

Use this instruction exactly in the frontend repository so generated UI/features match the current backend API and work end-to-end.

---

## Prompt You Can Paste Into Frontend Copilot

You are implementing a frontend that must integrate with an existing FastAPI backend for Optimos. Build production-ready, typed API integration and UI flows that match this contract exactly.

### 1) Core Requirements

- Do not invent endpoints.
- Use one API base URL config (for example from env): `API_BASE_URL`.
- Use bearer auth with access token + refresh token rotation.
- Implement centralized API client with:
  - JSON support
  - form-url-encoded support (for login)
  - automatic `Authorization: Bearer <access_token>`
  - automatic request id propagation (`X-Request-ID` optional generated client-side)
  - 401 handling with refresh retry once
  - consistent parsing of backend error envelope
- Implement route guards for authenticated pages.
- Implement optimistic-but-safe UX with loading, empty, and failure states on all data screens.

### 2) Auth Contract (Exact)

- Register:
  - `POST /api/auth/register`
  - JSON body: `{ email, username, password }`
  - Returns the created user with `is_active: false`; show a prompt to verify the email before login.
- Request email verification:
  - `POST /api/auth/email-verification/request`
  - JSON body: `{ email }`
  - Returns a generic accepted response.
- Confirm email verification:
  - `POST /api/auth/email-verification/confirm`
  - JSON body: `{ token }`
  - The frontend route `/verify-email?token=...` should submit the token and then direct the user to login.
- Request password reset:
  - `POST /api/auth/password-reset/request`
  - JSON body: `{ email }`
  - Returns a generic accepted response.
- Confirm password reset:
  - `POST /api/auth/password-reset/confirm`
  - JSON body: `{ token, password }`
  - The frontend route `/reset-password?token=...` should collect the new password and submit it.
- Login:
  - `POST /api/auth/login`
  - Content-Type: `application/x-www-form-urlencoded`
  - Fields: `username`, `password` (username can be username or email)
  - Returns: `{ access_token, refresh_token, token_type }`
  - Unverified accounts cannot log in.
- Refresh:
  - `POST /api/auth/refresh`
  - JSON body: `{ refresh_token }`
  - Returns new `{ access_token, refresh_token, token_type }`
  - Backend rotates refresh tokens; replace stored refresh token with new one.
- Logout:
  - `POST /api/auth/logout`
  - Requires bearer access token
  - Optional JSON body `{ refresh_token }` to revoke refresh token too
  - On success, clear local auth state.

### 3) Authenticated User/Profile APIs

- `GET /api/users/me`
- `GET /api/users/{user_id}` (only self unless admin)
- Profile bundle under `/api/users/me`:
  - `GET/PATCH /profile`
  - `GET/PATCH /notifications`
  - `GET/PATCH /security`

Build settings UI with separate sections:
- Personal profile
- Notification preferences
- Security settings (session timeout etc.)

### 4) Chat + AI Generation Flow

- Send prompt:
  - `POST /api/chats`
  - JSON body: `{ user_message }`
  - Optional header: `Idempotency-Key`
- IMPORTANT: When user presses submit, generate and send an idempotency key to prevent duplicate chat records on retries.
- Chat history:
  - `GET /api/chats?limit=<1..100>&offset=<>=0`
  - Response shape: `{ chats, total, limit, offset }`
- Delete one: `DELETE /api/chats/{chat_id}`
- Clear all: `DELETE /api/chats`

### 5) Subscription + Entitlements + Limits

- `GET /api/subscriptions/me`
- `POST /api/billing/subscription-intent` with `{ "tier": "pro" | "enterprise" }` to start paid checkout
- `POST /api/billing/customer-portal` to open Stripe subscription management
- `GET /api/subscriptions/usage`
- `GET /api/subscriptions/entitlements`

Use entitlements response as the feature gate source of truth:
- hide/disable unavailable premium actions
- show tier, usage remaining, and credits balance

### 6) Credits + Usage

- Wallet: `GET /api/credits/wallet`
- Transactions: `GET /api/credits/transactions?limit&offset`
- Feature costs: `GET /api/credits/feature-costs`
- Usage logs: `GET /api/usage/me?limit&offset`
- Start a credit purchase: `POST /api/billing/purchase-intent` with `credits`, `success_url`, and `cancel_url`; both URLs must use the configured frontend origin.

After returning from Checkout, refresh the wallet from the API; do not grant credits in the client.

Render:
- current credit balance
- transaction ledger with pagination
- feature cost table
- AI usage history (status, tokens, estimated cost, credits charged, time)

### 7) User Data CRUD Features

All are authenticated and user-scoped.

- Experiences:
  - `GET /api/experiences?limit&offset`
  - `POST /api/experiences`
  - `PATCH /api/experiences/{experience_id}`
  - `DELETE /api/experiences/{experience_id}`
- Opinions:
  - `GET /api/opinions?limit&offset`
  - `POST /api/opinions`
  - `PATCH /api/opinions/{opinion_id}`
  - `DELETE /api/opinions/{opinion_id}`
- Posts:
  - `GET /api/posts?limit&offset`
  - `POST /api/posts`
  - `PATCH /api/posts/{post_id}`
  - `DELETE /api/posts/{post_id}`

Standard paginated list response pattern is:
- `{ items, total, limit, offset }`

### 8) Admin Features (Role-Gated)

Only for users with admin access:
- `GET /api/admin/stats`
- `GET /api/admin/users`
- `GET /api/admin/chat-stats?days=7`
- `POST /api/credits/admin/adjust`

Implement admin-only routes and navigation visibility checks.
If API returns 403, redirect/show not-authorized page.

### 9) Global Error Handling Requirements

Backend returns structured errors like:

```json
{
  "error": {
    "code": "HTTP_401",
    "message": "Could not validate credentials",
    "status": 401,
    "request_id": "...",
    "path": "/api/users/me",
    "timestamp": "...",
    "details": {}
  },
  "detail": "Could not validate credentials"
}
```

Frontend must:
- parse both `error.message` and fallback `detail`
- surface helpful messages per status code:
  - 401: session expired/login required
  - 402: insufficient credits
  - 403: forbidden/plan or role restriction
  - 404: missing resource
  - 409: conflict (for admin credit adjustment edge cases)
  - 422: validation errors (show field-level when possible)
  - 429: too many requests or monthly message limit reached
  - 500: generic server error
- capture and log `error.request_id` for support/debug UI.

### 10) Rate Limit + Retry Behavior

Read and preserve these response headers:
- `X-RateLimit-Limit`
- `X-RateLimit-Remaining`
- `X-RateLimit-Window`
- `Retry-After` (on 429)
- `X-Request-ID`

Client behavior on 429:
- Show rate-limit banner/toast
- Disable repeated action briefly
- Use `Retry-After` where present before retrying

### 11) Health/Bootstrapping Endpoints

Public endpoints:
- `GET /`
- `GET /health`
- `GET /health/live`
- `GET /health/ready`

Use optional backend status indicator in frontend diagnostics/dev settings page.

### 12) Data Models To Mirror In Frontend Types

Create strict TypeScript interfaces/types for:
- Token payload
- User
- Profile
- NotificationPreferences
- SecuritySettings
- ChatResponse + ChatHistory
- Subscription + Entitlements + Usage summary
- CreditWallet, CreditTransaction, FeatureCost
- AIUsage
- Experience, Opinion, UserPost
- Standard paginated response wrapper
- Structured API error envelope

### 13) Required UX Screens

Implement at minimum:
- Auth: Register, Login, Logout flow
- Dashboard: summary cards (subscription, credits, recent usage)
- Chat composer + chat history
- Profile/settings page (profile/notifications/security)
- Experiences manager (CRUD)
- Opinions manager (CRUD)
- Posts manager (CRUD)
- Subscription page (tier, usage, upgrade)
- Credits page (wallet, costs, transactions)
- Usage page (AI usage logs)
- Admin page (stats, users, chat stats, credit adjustment)

### 14) Acceptance Checklist

The implementation is complete only when:
- Auth works end-to-end including refresh rotation.
- Chat submission uses idempotency key and duplicate submit does not duplicate records.
- Pagination works for all list endpoints.
- Entitlements drive feature gating in UI.
- Rate limits and 429 handling are user-friendly.
- Error envelope is parsed consistently across app.
- Role-based admin routes are protected.
- All API calls are centralized and typed.

Generate code in small, reviewable commits/modules: API client, auth store, feature services, then pages/components.

---

## Notes For Frontend Developer

- Backend defaults allow frontend origins like localhost 3000 and 5173.
- Login endpoint is OAuth2 form-data, not JSON.
- Monthly message limit and credit balance are different constraints; UI should communicate both.
- Some generated AI features may be entitlement-gated even if visible in UI, so always handle backend 403 gracefully.
