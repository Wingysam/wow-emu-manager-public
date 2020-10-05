FROM python:3.6-slim
RUN pip install tornado

WORKDIR /app
COPY . /app

ENV CONFIG="/config/config.json"

CMD python main.py
