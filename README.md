# 🧩 Media Service Platform API

A Django REST Framework (DRF)-based backend for a platform where users can browse a gallery (images, audio, video), request changes to media files, chat with admins in real-time, and pay for services.

---

## 🚀 Features

- 👥 Two user types: **End User** and **Admin**
- 🖼 Media gallery with support for images, audios, videos, and other files
- ✍️ Users can request edits for any media item
- 🔁 Admins respond by editing files manually and uploading results
- 💬 Real-time chat between users and admins
- 💳 Univapay integration for handling payments (charges, subscriptions, refunds)
- 🐳 Dockerized for easy local development and deployment

---


---
## Clone the repository

```bash
  git clone https://github.com/jbcayan/Project-F-Backend.git
```

## move to project directory

```bash
  cd Project-F-Backend
```

## 📦 Install dependencies

```bash
  pip install -r requirements.txt
```

## Create .env from example

```bash
  cp env-example .env
```

## Root directory

```bash
  cd project
```

## Run migrations

```bash
  python manage.py migrate
```

## Create superuser

```bash
  python manage.py createsuperuser
```


## 🐳 Run with Docker

Make sure you have **Docker** and **Docker Compose** installed.

### 🔧 Step-by-Step

```bash
# 3. Build and run the containers
    docker-compose up --build


# Run migrations
    docker-compose exec f_backend python manage.py migrate

# Create superuser
    docker-compose exec f_backend python manage.py createsuperuser

# Collect static files
    docker-compose exec f_backend python manage.py collectstatic

# Access shell
    docker-compose exec f_backend python manage.py shell
```


```bash
docker exec -it f_backend bash
```

## 🔐 Environment Variables

Copy `env-example` to `.env` and set the following:

- Core
  - `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS`
  - Database: `DATABASE_TYPE`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`
  - Email: `EMAIL_BACKEND`, `EMAIL_HOST`, `EMAIL_USE_TLS`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`

- Payments (Univapay)
  - `UNIVAPAY_MODE`: `test` or `live`
  - `UNIVAPAY_BASE_URL`: API base (default `https://api.univapay.com`)
  - Live creds (used when `UNIVAPAY_MODE=live`): `UNIVAPAY_APP_TOKEN`, `UNIVAPAY_APP_SECRET`, `UNIVAPAY_STORE_ID`
  - Test creds (used when `UNIVAPAY_MODE=test` or for forced-test users): `UNIVAPAY_TEST_APP_TOKEN`, `UNIVAPAY_TEST_APP_SECRET`, `UNIVAPAY_TEST_STORE_ID`, `UNIVAPAY_TEST_BASE_URL`
  - Webhooks: `UNIVAPAY_WEBHOOK_AUTH` (HMAC secret for verifying `X-Signature`)

- Forced Test Users
  - `TEST_PAYMENT_USERS`: comma-separated `email:password` pairs (these users always use Univapay test mode and are auto-created if missing)

### Forced Test Users Behavior
- On app startup, users listed in `TEST_PAYMENT_USERS` are created if missing (using the provided per-user password).
- For these users, all payment flows and `GET /payment/widget-config/` will operate in test mode even if `UNIVAPAY_MODE=live`.

## 📘 Payment Endpoints (key)
- Widget config: `GET /payment/widget-config/`
- Create charge: `POST /payment/univapay/charge/`
- Create subscription: `POST /payment/univapay/subscription/`
- Cancel subscription: `POST /payment/univapay/cancel-subscription/`
- Refund charge: `POST /payment/univapay/refund-charge/`
- Payment status: `POST /payment/univapay/payment-status/`
- Webhook: `POST /payment/webhook/univapay/` (set `UNIVAPAY_WEBHOOK_AUTH`)

Note: Test vs live is controlled by `UNIVAPAY_MODE`; forced-test users always use test credentials.