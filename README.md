# Seharta Backend

Backend API for Seharta financial management application built with FastAPI

## Tech Stack

* FastAPI
* SQLAlchemy
* PostgreSQL (Supabase)
* JWT Authentication
* Google OAuth
* Alembic

## Setup

### Create Virtual Environment

```bash
python -m venv venv
```

### Activate Virtual Environment

```bash
venv\Scripts\activate
```

### Install Dependencies

```bash
pip install -r requirements.txt
```

### Setup Environment Variables

Create `.env` file based on `.env.example`.

### Run Development Server

```bash
uvicorn app.main:app --reload
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

## API Docs

Swagger UI:

```txt
http://127.0.0.1:8000/docs
```
