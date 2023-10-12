#FROM ubuntu:20.10
FROM python:3.8-slim
#RUN apt-get update -y && apt-get install -y python3-pip python-dev

WORKDIR /app

COPY requirements.txt /app/requirements.txt

RUN pip3 install -r /app/requirements.txt

COPY security/token /app
COPY security/ca.crt /app

COPY admission_controller.py /app

COPY wsgi.py /app

ENV KUBE_API_SERVER https://127.0.0.1:45326

CMD gunicorn --certfile=/certs/webhook.crt --keyfile=/certs/webhook.key --bind 0.0.0.0:443 wsgi:webhook
