# Capital Works Web Portal

Next.js (App Router) frontend for the Capital Works FastAPI backend.

## Getting Started

Create a local environment file:

```bash
cp .env.local.example .env.local
```

Update `NEXT_PUBLIC_API_BASE_URL` to your FastAPI URL.

Start the development server:

```bash
npm run dev
```

Open `http://localhost:3000`.

## Routes

- `/login`
- `/user/new-task`
- `/admin/tasks`
- `/admin/summary`
- `/admin/users`

## Build

```bash
npm run build
npm run start
```
