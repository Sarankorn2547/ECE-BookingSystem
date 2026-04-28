#!/bin/sh

if [ "$DATABASE" = "postgres" ]
then
    echo "Waiting for postgres..."

    while ! nc -z $SQL_HOST $SQL_PORT; do
      sleep 0.1
    done

    echo "PostgreSQL started"
fi

# Print structure for debugging (Optional, can be removed after success)
echo "Current directory structure:"
ls -F

# Run migrations
python manage.py migrate --noinput
# Collect static files
python manage.py collectstatic --noinput

exec "$@"
