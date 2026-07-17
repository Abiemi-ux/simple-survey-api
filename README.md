# Sky Survey Platform — API

A Django REST Framework API for a survey platform. All requests and
responses are XML (no JSON anywhere in the API surface).

## Live Demo

- **API base URL:** https://simple-survey-api-iow2.onrender.com/api
- **Example endpoint:** https://simple-survey-api-iow2.onrender.com/api/surveys
- **Admin panel:** https://simple-survey-api-iow2.onrender.com/admin/

> Hosted on Render's free tier — the service spins down after periods of
> inactivity, so the first request after idle time may take 30–60 seconds
> to respond while it wakes up.

## Prerequisites

- Python 3.12+
- PostgreSQL (this project is configured against a Render-hosted Postgres
  instance, but any Postgres instance works)
- `pip` and `venv`

## Installation

```bash
git clone https://github.com/<your-username>/simple-survey-api.git
cd simple-survey-api

python -m venv venv
venv\Scripts\activate        # macOS/Linux: source venv/bin/activate

pip install -r requirements.txt

cp .env.example .env         # then fill in your own values
```

`.env` needs:
```
DATABASE_URL=postgresql://user:password@host:5432/dbname
SECRET_KEY=your-secret-key-here
DEBUG=True
```

```bash
python manage.py migrate
python manage.py createsuperuser
```

## Running locally

```bash
python manage.py runserver 8000
```

- Admin panel: `http://127.0.0.1:8000/admin/`
- API root: `http://127.0.0.1:8000/api/surveys`

Import [`postman_collection.json`](./postman_collection.json) into Postman
for documented example requests against every endpoint.

## Technologies used

- Django + Django REST Framework
- PostgreSQL (hosted on Render)
- Custom XML renderer/parser (`surveys/xml_codec.py`) — DRF's default
  renderers are JSON-based, so requests/responses are hand-encoded/decoded
  to and from XML
- `django-cors-headers` — allows the separately-hosted web app
  (`simple-survey-web`) to call this API cross-origin
- `python-decouple` / `django-environ` — loads secrets from `.env`, kept out
  of version control
- Token-free session auth (`SessionAuthentication`) with CSRF enforcement
  on write endpoints, gated per-view via `get_permissions()`

## Assumptions made

- The API has no user-facing registration flow — admin access is limited
  to the Django superuser created via `createsuperuser`; there's no
  self-serve "sign up as an admin" endpoint.
- Survey responses and question reads are intentionally public/unauthenticated,
  since respondents filling out a survey shouldn't need an account.
  Writes to surveys/questions and the responses *list* require login.
- File uploads (certificates) are stored on the local filesystem rather than cloud object storage.
  This is acceptable for the scope of this task, but on Render these files exist only
  for the lifetime of a running application instance. They are lost whenever the service is
  restarted or redeployed because the filesystem is ephemeral.
- One survey response = one submission; there's no draft-saving or
  resuming a partially-completed survey.
