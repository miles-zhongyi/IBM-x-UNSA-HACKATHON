# Frontend (Next.js 14)

## Run

1. Start the API (repo root):

```bash
pip install -r backend/requirements.txt
uvicorn backend.api.main:app --reload --port 8000
```

2. Start the web app:

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:3000`.

## Configuration

Optional: `frontend/.env.local`

```
NEXT_PUBLIC_API_BASE=http://127.0.0.1:8000
```

You can also change the API base URL from the patient screen (session state; not stored in `localStorage`).

## PWA

`app/manifest.ts` provides a web app manifest. Add real PNG icons later if you need broader install support on Android.
