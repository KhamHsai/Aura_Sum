# Smart Receipt Project — Step 20: Vue Frontend Foundation and Authentication

## Goal

Create the frontend foundation and complete this working flow:

```text
Register
→ Login
→ Save access token
→ Load current user
→ Open protected dashboard
→ Logout
```

Use:

```text
Vue 3
TypeScript
Vite
Pinia
Vue Router
Axios
Vue I18n
```

Write simple, human-readable code that is easy to understand and explain. Avoid unnecessary abstractions, complex design patterns, generic frameworks, and overengineering.

## Backend Status

The backend is complete and ready for frontend integration.

Authentication endpoints:

```text
POST /api/auth/register
POST /api/auth/login
GET  /api/auth/me
```

Do not change backend business logic unless a real integration bug is found.

## Scope

Implement only:

- Vue project setup
- TypeScript and Vite
- Vue Router
- Pinia
- Axios API client
- Authentication API functions
- Authentication store
- Token persistence
- Login page
- Register page
- Protected dashboard
- Route guards
- Logout
- Basic English/Thai frontend labels
- Basic app layout
- Focused frontend tests
- Production build verification

Do not implement expense pages, receipt upload, Gemini extraction UI, translation buttons, Excel export button, or dashboard statistics yet.

## Coding Style

1. Use clear names and straightforward logic.
2. Keep API calls in small API modules.
3. Keep auth state in one Pinia store.
4. Keep route guards simple.
5. Use TypeScript without complicated generic types.
6. Avoid unnecessary composables, classes, repositories, and frameworks.
7. Use plain CSS unless a UI framework is already installed.

## Inspect Existing Frontend

Check whether the project already has:

```text
frontend/
package.json
vite.config.*
src/
```

If it exists, reuse it and do not overwrite unrelated work.

If it does not exist, create a Vue 3 + TypeScript + Vite app in:

```text
frontend/
```

Install only:

```text
vue-router
pinia
axios
vue-i18n
```

## Recommended Structure

```text
frontend/
├── .env.example
├── package.json
├── tsconfig.json
├── vite.config.ts
└── src/
    ├── api/
    │   ├── axios.ts
    │   └── authApi.ts
    ├── stores/
    │   └── auth.ts
    ├── router/
    │   └── index.ts
    ├── layouts/
    │   └── AppLayout.vue
    ├── views/
    │   ├── LoginView.vue
    │   ├── RegisterView.vue
    │   └── DashboardView.vue
    ├── locales/
    │   ├── en.json
    │   └── th.json
    ├── types/
    │   └── auth.ts
    ├── App.vue
    ├── main.ts
    └── style.css
```

## Environment

Create:

```text
frontend/.env.example
```

with:

```env
VITE_API_BASE_URL=http://127.0.0.1:8000/api
```

The real local file should be:

```text
frontend/.env
```

Do not commit the real `.env`.

Use:

```ts
import.meta.env.VITE_API_BASE_URL
```

Do not hard-code the backend URL across components.

## Axios Client

Create:

```text
src/api/axios.ts
```

Requirements:

- Use `VITE_API_BASE_URL`
- Add JSON headers
- Add `Authorization: Bearer <token>` when a token exists
- Handle `401` simply
- Clear invalid auth data
- Avoid redirect loops
- Never log tokens

## Types

Inspect the actual backend responses first.

Suggested simple types:

```ts
export interface User {
  id: number
  email: string
}

export interface LoginRequest {
  email: string
  password: string
}

export interface RegisterRequest {
  email: string
  password: string
}

export interface LoginResponse {
  access_token: string
  token_type: string
}
```

Use only fields the backend really returns.

## Authentication API

Create:

```text
src/api/authApi.ts
```

Functions:

```ts
registerUser(data)
loginUser(data)
getCurrentUser()
```

Inspect whether login expects JSON or form data and match it exactly.

Do not handle navigation inside the API module.

## Authentication Store

Create:

```text
src/stores/auth.ts
```

State:

```text
token
user
isLoading
error
```

Computed:

```text
isAuthenticated
```

Actions:

```text
register
login
loadCurrentUser
logout
initializeAuth
```

Behavior:

### Login

```text
1. Call login endpoint
2. Save token in store
3. Save token in localStorage
4. Call /api/auth/me
5. Save current user
```

### Register

```text
1. Register user
2. Redirect to login
```

Use the actual backend behavior if registration returns something different.

### Initialize

```text
1. Read token from localStorage
2. Call /api/auth/me
3. Store user if valid
4. Clear token if invalid
```

### Logout

```text
1. Clear store
2. Remove token from localStorage
3. Redirect to login
```

Do not implement refresh tokens.

## Router

Create routes:

```text
/login
/register
/dashboard
```

Use route meta:

```ts
meta: {
  requiresAuth: true
}
```

for the dashboard.

Add a simple global guard:

```text
Protected route + no valid auth → /login
Authenticated user opens /login or /register → /dashboard
Unknown route → /dashboard or /login based on auth state
```

## App Initialization

Call:

```text
authStore.initializeAuth()
```

before protected navigation is trusted.

Use a simple loading state to avoid showing the wrong page during auth restoration.

## Login Page

Create:

```text
src/views/LoginView.vue
```

Fields:

```text
Email
Password
```

Include:

- Required validation
- Loading state
- Safe error message
- Link to registration
- Accessible labels

Do not store the password.

## Register Page

Create:

```text
src/views/RegisterView.vue
```

Use backend-required fields.

At minimum:

```text
Email
Password
Confirm Password
```

Validate:

- Required fields
- Valid email
- Passwords match
- Password minimum matching backend rules

After success:

```text
Show success
Redirect to login
```

## Protected Layout

Create:

```text
src/layouts/AppLayout.vue
```

Include:

```text
App name
Current user email
Language switcher
Logout button
Router view
```

Keep it basic.

## Dashboard

Create:

```text
src/views/DashboardView.vue
```

Display only:

```text
Welcome message
Current user email
Backend connection success
Placeholder for future expense features
```

Do not add fake statistics.

## English and Thai UI Labels

Use Vue I18n.

Create:

```text
src/locales/en.json
src/locales/th.json
```

Translate fixed labels such as:

```text
Login
Register
Email
Password
Confirm Password
Logout
Dashboard
Welcome
Loading
Save
Cancel
```

Support only:

```text
en
th
```

Default to English.

Persist the selected language in localStorage.

Do not use Gemini for fixed frontend labels.

## Styling

Use simple responsive CSS:

- Centered auth card
- Clear buttons
- Visible errors
- Simple top navigation
- Mobile-friendly spacing

Do not add Tailwind, Bootstrap, or another UI library unless already installed.

## CORS

Frontend development origin:

```text
http://localhost:5173
```

Backend:

```text
http://127.0.0.1:8000
```

Inspect backend CORS settings.

Allow explicitly:

```text
http://localhost:5173
http://127.0.0.1:5173
```

only if needed.

Do not use unrestricted production CORS.

## Error Messages

Handle:

```text
Invalid email or password
Email already registered
Validation error
Backend unavailable
Session expired
```

Do not display raw stack traces or tokens.

## Frontend Tests

Use the existing frontend test setup.

If none exists, add:

```text
Vitest
Vue Test Utils
```

Test at least:

1. Login stores token.
2. Current user loads.
3. Invalid session clears token.
4. Logout clears store and localStorage.
5. Protected route redirects to login.
6. Authenticated user reaches dashboard.
7. Authenticated user is redirected away from login.
8. Login submits valid data.
9. Login shows backend error.
10. Registration validates matching passwords.
11. Registration calls API.
12. Language switches English/Thai.
13. Language preference persists.
14. Password is never saved in localStorage.
15. Axios sends Bearer token.

Mock all backend calls.

Do not require the real FastAPI server for unit tests.

## Manual Verification

Run backend:

```bash
cd backend
source venv/bin/activate
uvicorn app.main:app --reload
```

Run frontend in another terminal:

```bash
cd frontend
npm install
npm run dev
```

Open:

```text
http://localhost:5173
```

Manually test:

```text
Register
Login
Dashboard
Refresh page
Current user remains loaded
Switch English/Thai
Logout
Protected route redirects to login
```

## Build Verification

Run:

```bash
npm run build
```

Run the actual configured frontend test script:

```bash
npm run test
```

or:

```bash
npm run test:unit
```

## Do Not Implement Yet

- Expense list and detail
- Manual expense form
- Receipt upload
- Gemini extraction UI
- Confirmation UI
- Dynamic translation button
- Excel export button
- Dashboard statistics
- Admin pages
- Password reset
- Social login

## Expected Result

After this step:

- Vue 3 + TypeScript + Vite
- Pinia auth store
- Vue Router
- Axios client
- Register and login pages
- Protected dashboard
- Token persistence
- Current-user restoration
- Logout
- Fixed English/Thai UI labels
- Responsive basic styling
- Focused frontend tests
- Successful build

## Completion Report

Provide:

1. Existing frontend status found
2. Files created or changed
3. Packages installed
4. API base URL setup
5. Login request format confirmed
6. Auth store behavior
7. Token storage behavior
8. Router guard behavior
9. Pages created
10. English/Thai setup
11. CORS changes
12. Test result
13. Build result
14. Manual verification result
15. Any backend/frontend mismatch

Do not produce a long walkthrough unless an error occurs.
