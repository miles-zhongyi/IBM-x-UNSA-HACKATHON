# Frontend (React + CRACO)

This frontend was integrated from:
https://github.com/hheain/IBM-frontend_new/tree/main

## Run locally

1. Start backend API from repo root:

```bash
pip install -r backend/requirements.txt
uvicorn backend.api.main:app --reload --port 8000
```

2. Configure frontend environment:

```bash
cd frontend
copy .env.example .env
```

3. Install and run frontend:

```bash
npm install
npm start
```

Open `http://localhost:3000`.

## Environment variables

`frontend/.env`:

```env
REACT_APP_BACKEND_URL=http://127.0.0.1:8000
```

If unset, the app now falls back to `http://127.0.0.1:8000`.
