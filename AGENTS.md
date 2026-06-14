## Dev

```bash
# Terminal 1: Flask API
python web/app.py

# Terminal 2: React dev server (hot reload, proxies /api to Flask)
cd web/react-app && npm run dev

# Production build
cd web/react-app && npm run build
# Flask auto-serves dist/ when it exists
```

## Stack

- **Backend**: Flask (port 5000), REST API at `/api/*`
- **Frontend**: React + TypeScript + Vite
- **State**: Zustand (`configStore.ts`)
- **API**: TanStack Query (`hooks/useApi.ts`)

## Lint/Check

```bash
cd web/react-app && npx tsc --noEmit && npx eslint .
```
