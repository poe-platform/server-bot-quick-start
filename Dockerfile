FROM python:3.11.3-slim-buster

WORKDIR /app

COPY main.py .
COPY echobot.py .
COPY langcatbot.py .
COPY catbot catbot
COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
