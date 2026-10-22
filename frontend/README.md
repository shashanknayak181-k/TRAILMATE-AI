# TRAILMATE AI frontend

React + TypeScript + Vite customer entry flow. The app uses the backend API through Vite's `/api` proxy in development; session cookies are HttpOnly and are not stored in browser local storage.

## Run

```bash
npm install
npm run dev
npm run build
```

Set up and run the backend first (see the repository root README). The development-only email verification code is displayed in the UI because no real email provider is configured. Do not use that delivery mode in production.
