Your README is already strong. I’d update it mainly to:

* include live deployment URLs
* explain architecture more clearly
* make it look more production-grade
* improve recruiter/interviewer readability

Here’s the upgraded version you should replace it with:

````md
# Breathe ESG Data Ingestion Prototype

Enterprise-style ESG ingestion and analyst review platform built with Django REST Framework, PostgreSQL, React, Vite, and Tailwind CSS.

## Live Deployment

Frontend:
https://breathe-esg-dun.vercel.app

Backend API:
https://breathe-esg-lhb2.onrender.com/api/records/

GitHub Repository:
https://github.com/abhishekkraj099/Breathe-ESG

---

## Overview

This prototype simulates how enterprise sustainability platforms ingest, validate, normalize, review, and audit ESG operational data from multiple internal systems.

The application focuses on:
- ingestion traceability
- suspicious data detection
- analyst review workflows
- audit readiness
- normalized emissions calculations

The system accepts raw CSV exports from:
- SAP fuel/procurement systems
- utility electricity billing portals
- corporate travel expense systems

Each uploaded row is preserved in raw form while also being normalized into a structured ESG emissions record.

---

## Features

### Data Ingestion
- Upload enterprise CSV exports
- Multi-source ingestion pipeline
- Batch tracking and upload summaries
- Raw JSON preservation for audit traceability

### ESG Processing
- Scope classification
- Quantity normalization
- Unit conversion
- kg CO2e emissions calculations

### Analyst Review Workflow
- Suspicious row detection
- Pending / Approved / Rejected review states
- Analyst review actions
- Review notes and audit logging

### Enterprise-Oriented Behaviors
- Source traceability
- Batch-based ingestion
- PostgreSQL persistence
- REST API architecture
- Production deployment

---

## Tech Stack

### Backend
- Django
- Django REST Framework
- PostgreSQL
- Gunicorn

### Frontend
- React
- Vite
- Tailwind CSS

### Deployment
- Render (Backend + PostgreSQL)
- Vercel (Frontend)

---

## Architecture

```text
Frontend (React + Vercel)
        ↓
Django REST API (Render)
        ↓
PostgreSQL Database (Render)
````

---

## Folder Structure

```text
backend/
  config/              Django settings and URLs
  ingestion/           Models, serializers, parsers, views
  manage.py

frontend/
  src/                 React analyst dashboard

sample_data/
  sap_fuel_procurement.csv
  utility_electricity.csv
  corporate_travel.csv

MODEL.md
DECISIONS.md
TRADEOFFS.md
SOURCES.md
README.md
render.yaml
requirements.txt
```

---

## Sample Data

The repository includes realistic enterprise-style datasets inside `sample_data/`.

### SAP Fuel & Procurement

* German-style SAP column headers
* Plant-based fuel usage
* Diesel, LPG, petrol, and marine fuel examples
* Intentional bad rows for parser validation

### Utility Electricity

* Multi-meter electricity billing exports
* Real Indian utility providers
* Billing-period inconsistencies
* Missing kWh validation cases

### Corporate Travel

* Domestic and international routes
* Air, hotel, rail, and car categories
* Missing travel distance and amount scenarios

The datasets intentionally contain suspicious rows to simulate real analyst-review workflows.

---

## Backend Setup

```bash
python -m venv .venv
.venv\Scripts\activate

pip install -r requirements.txt

cd backend

python manage.py migrate
python manage.py runserver
```

Backend default:

```text
http://localhost:8000/api
```

The backend automatically uses `DATABASE_URL` when deployed on Render/PostgreSQL.

---

## Frontend Setup

```bash
cd frontend

npm install
npm run dev
```

Frontend default:

```text
http://localhost:5173
```

Configure API endpoint with:

```env
VITE_API_BASE=http://localhost:8000/api
```

---

## API Endpoints

### Upload CSV

```http
POST /api/upload/
```

Multipart form fields:

* `source_type`
* `file`
* optional `uploaded_by`
* optional `client_name`

Supported source types:

* `SAP_FUEL`
* `UTILITY_ELECTRICITY`
* `CORPORATE_TRAVEL`

---

### Retrieve Records

```http
GET /api/records/
```

Supported filters:

* `review_status`
* `flagged=true`
* `source_type`

---

### Review Actions

```http
PATCH /api/records/:id/review/
```

Example payload:

```json
{
  "review_status": "APPROVED",
  "reviewed_by": "analyst",
  "note": "validated against source export"
}
```

---

### Retrieve Batches

```http
GET /api/batches/
```

---

## Review Workflow

1. Upload enterprise export
2. Parser validates and normalizes rows
3. Suspicious records are flagged
4. Analyst reviews records
5. Records are approved or rejected
6. Actions are stored in audit logs

---

## Design Decisions

Additional project notes:

* `MODEL.md`
* `DECISIONS.md`
* `TRADEOFFS.md`
* `SOURCES.md`

These documents explain:

* data modeling choices
* ingestion architecture
* parser tradeoffs
* emissions assumptions
* source references

---

## Deployment Notes

### Frontend

Hosted on Vercel.

### Backend

Hosted on Render using Gunicorn.

### Database

Hosted on Render PostgreSQL.

Environment variables:

* `SECRET_KEY`
* `DEBUG`
* `ALLOWED_HOSTS`
* `CORS_ALLOWED_ORIGINS`
* `DATABASE_URL`
* `VITE_API_BASE`

---

## Future Improvements

Potential next steps:

* async ingestion queues
* duplicate detection rules
* file versioning
* role-based analyst access
* emissions factor management
* audit export reports
* ingestion retry workflows

---

## Author

Abhishek Raj

```
```
