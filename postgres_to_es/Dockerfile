FROM python:3.10

WORKDIR /etl

RUN apt-get update

COPY requirements.txt requirements.txt

RUN  pip install --upgrade pip \
     && pip install -r requirements.txt

COPY . .

RUN groupadd -r user && useradd -r -g user user

RUN chown user:user -R /etl

USER user

ENTRYPOINT ["python3", "/etl/app_etl.py"]
