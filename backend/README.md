# Capital Works Backend

This backend provides FastAPI endpoints backed by Excel files only. It uses file locks for all Excel operations.

## Quick start (local)

1. Create a virtual environment and install dependencies:

```bash
cd backend
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

2. Create the initial admin user:

```bash
python -m app.create_admin
```

3. Start the API server:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

The data files are created automatically if missing:
- `backend/data/users.xlsx`
- `backend/data/tasks.xlsx`

## Configure the Tkinter client

Set the API base URL (optional if running on localhost):

```bash
set CAPITAL_WORKS_API=http://localhost:8000
```

Then run the UI from the project root:

```bash
python app.py
```

## Admin reporting endpoints (Phase 3)

All admin endpoints require a valid admin JWT.

### GET /admin/tasks

Query params:
- `sort_by`: any task column (default `sno`)
- `order`: `asc` or `desc` (default `asc`)
- `sub_division`: optional contains filter
- `account_code`: optional `Spill` or `New`
- `date_from`: optional ISO date or datetime (inclusive)
- `date_to`: optional ISO date or datetime (inclusive)
- `page`: default `1`
- `page_size`: default `50`, max `500`

Example:

```
GET /admin/tasks?sort_by=created_at&order=desc&sub_division=North&account_code=Spill&date_from=2025-01-01&page=1&page_size=50
```

### GET /admin/summary

Same filter params as `/admin/tasks` (no sorting or pagination). Returns grand totals and sub-division totals.

Example:

```
GET /admin/summary?sub_division=North&date_from=2025-01-01&date_to=2025-06-30
```

### GET /admin/export

Same filters and sorting as `/admin/tasks`. Returns an Excel file download with a summary section appended.
The backend creates or overwrites `backend/data/tasks_backup.xlsx` before generating the export.

Example:

```
GET /admin/export?sort_by=created_at&order=desc&account_code=New
```

## Deployment notes

- Use a VM or any server with a persistent disk.
- Do not deploy on stateless serverless platforms.
- Set a secure `JWT_SECRET` environment variable in production.
