#!/bin/bash

# Exit immediately if a command exits with a non-zero status
set -e

# Navigate to the project directory
cd /app/project

# Wait for Redis to be ready
echo "Waiting for Redis..."
while ! nc -z alibi_redis 6379; do
  sleep 1
done
echo "Redis is up!"

# Apply database migrations
echo "Applying migrations..."
python manage.py migrate --noinput

# Ensure staticfiles directory exists
#echo "Ensuring staticfiles directory exists..."
#mkdir -p /app/staticfiles

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --noinput --clear -v 2 || echo "Static files collection failed but continuing."

# Start Celery worker in the background
echo "Starting Celery worker..."
celery -A project worker --loglevel=info &
#
## Start Celery beat in the background
echo "Starting Celery beat..."
celery -A project beat --loglevel=info &

echo "Starting Django development server..."
#python manage.py runserver 0.0.0.0:8000

# Start the Gunicorn server
exec gunicorn project.wsgi:application --bind 0.0.0.0:8000