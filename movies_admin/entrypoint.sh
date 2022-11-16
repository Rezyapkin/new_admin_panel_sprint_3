#!/bin/sh

set -e

if [ "$DATABASE" = "postgres" ]
then
    echo "Waiting for postgres..."

    while ! nc -z $SQL_HOST $SQL_PORT; do
      sleep 0.1
    done

    echo "PostgresSQL started"
fi

python manage.py flush --no-input
python manage.py migrate

if [ `ls /opt/app/static/ | wc -l` -eq 0 ]
then
    python manage.py collectstatic --no-input --clear
fi

exec "$@"