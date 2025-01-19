FROM python:3.10.9
workdir /usr/local/app

COPY ./ ./
EXPOSE 8080
RUN apt-get update && apt-get install -y libsndfile1-dev && apt-get install -y python3
RUN python3 -m pip install requirements.txt

CMD ["uvicorn", "main:app"]

