FROM python:3.10.9
workdir /usr/local/app

COPY ./ ./
EXPOSE 8080

RUN apt-get update && apt-get install -y libsndfile1-dev
RUN python3 -m pip install --no-cache-dir -r requirements.txt

CMD ["uvicorn", "main:app"]

