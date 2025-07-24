# 🧩 Media Service Platform API

A Django REST Framework (DRF)-based backend for a platform where users can browse a gallery (images, audio, video), request changes to media files, chat with admins in real-time, and pay for services via Stripe.

---

## 🚀 Features

- 👥 Two user types: **End User** and **Admin**
- 🖼 Media gallery with support for images, audios, videos, and other files
- ✍️ Users can request edits for any media item
- 🔁 Admins respond by editing files manually and uploading results
- 💬 Real-time chat between users and admins
- 💳 Stripe integration for handling payments
- 🐳 Dockerized for easy local development and deployment

---


---
## Clone the repository

```bash
  git clone https://github.com/your-username/media-service-platform.git
```

## move to project directory

```bash
  cd Project-F-Backend
```

## 📦 Install dependencies

```bash
  pip install -r requirements.txt
```

## create .env file for env-example

```bash
  cp .env.example .env
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