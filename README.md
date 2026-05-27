# Breathe ESG Data Ingestion Prototype

Production-style prototype for ingesting enterprise ESG source exports with Django REST Framework, PostgreSQL, React, Vite, and Tailwind CSS.

## Live Deployment

Frontend:
https://breathe-esg-dun.vercel.app

Backend API:
https://breathe-esg-lhb2.onrender.com/api/records/

GitHub Repository:
https://github.com/abhishekraj099/Breathe-ESG


## Screenshot
<img width="1890" height="1012" alt="image" src="https://github.com/user-attachments/assets/ac34a427-186d-4def-89d4-59b4b9a8f1b6" />
<img width="1905" height="967" alt="image" src="https://github.com/user-attachments/assets/4169237c-daeb-4708-989a-fa08de08a729" />
<img width="1893" height="960" alt="image" src="https://github.com/user-attachments/assets/371b2551-987f-4cad-8580-111cbd3b3054" />
<img width="1896" height="875" alt="image" src="https://github.com/user-attachments/assets/b7bf4ee3-13cf-4ae9-8805-3c96286280e2" />
<img width="1893" height="966" alt="image" src="https://github.com/user-attachments/assets/16f693b2-4e1d-4563-995a-803157c87206" />
<img width="1912" height="967" alt="image" src="https://github.com/user-attachments/assets/56c77b81-04e6-4eb5-b7e5-f64b272a29d6" />

## What It Does

- Uploads SAP fuel/procurement, utility electricity, and corporate travel CSV exports.
- Preserves every raw row as JSON for source traceability.
- Normalizes quantities and calculates kg CO2e.
- Flags suspicious rows for analyst review.
- Supports approve/reject review actions.
- Writes audit logs for ingestion and review changes.

## Folder Structure

```text
backend/
  config/              Django settings and URLs
  ingestion/           Models, serializers, views, parsers
  manage.py
frontend/
  src/                 React dashboard
sample_data/           Realistic CSV exports with intentional bad rows
MODEL.md
DECISIONS.md
TRADEOFFS.md
SOURCES.md
render.yaml
requirements.txt
```

## Backend Setup

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
cd backend
python manage.py migrate
python manage.py runserver
```

The backend uses `DATABASE_URL` when present, which is the Render/PostgreSQL path. Without it, it falls back to SQLite for local review.

## Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`. The frontend calls `http://localhost:8000/api` by default. Override with `VITE_API_BASE`.

## API

- `POST /api/upload/`
  - multipart fields: `source_type`, `file`, optional `uploaded_by`, optional `client_name`
  - source types: `SAP_FUEL`, `UTILITY_ELECTRICITY`, `CORPORATE_TRAVEL`
- `GET /api/records/`
  - filters: `review_status`, `flagged=true`, `source_type`
- `PATCH /api/records/:id/review/`
  - JSON: `{ "review_status": "APPROVED", "reviewed_by": "analyst", "note": "..." }`
- `GET /api/batches/`

## Sample Uploads

Use files in `sample_data/`:

- `sap_fuel_procurement.csv`
- `utility_electricity.csv`
- `corporate_travel.csv`

They include intentional bad rows for zero quantity, missing quantities, unknown plants, duplicate SAP document numbers, missing kWh, and missing travel amounts/distances.

## Render Deployment

`render.yaml` defines:

- Django web service running Gunicorn.
- Render PostgreSQL database.
- Static Vite frontend service.

After creating the Render blueprint, update `ALLOWED_HOSTS`, `CORS_ALLOWED_ORIGINS`, and `VITE_API_BASE` if Render assigns different hostnames.

