FROM python:3.10

WORKDIR /opt/app

ENV APP_DIR=/opt/app
ENV DJANGO_SETTINGS_MODULE 'config.settings'
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV UWSGI_PROCESSES 1
ENV UWSGI_THREADS 16
ENV UWSGI_HARAKIRI 240

COPY entrypoint.sh entrypoint.sh
COPY requirements.txt requirements.txt
COPY uwsgi/uwsgi.ini uwsgi.ini

RUN apt-get update \
    && apt-get install netcat -y

RUN  mkdir -p $APP_DIR/static/ \
     && mkdir -p $APP_DIR/media/ \
     && pip install --upgrade pip \
     && pip install -r requirements.txt

COPY . $APP_DIR

RUN chown www-data:www-data -R /opt/app /var/log

EXPOSE 8000

USER www-data

ENTRYPOINT ["./entrypoint.sh", "uwsgi", "--strict", "--ini", "uwsgi.ini"]
