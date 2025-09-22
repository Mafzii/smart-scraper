# Not-so-smart Scraper

A simple project for extracting data from websites using SLMs.

## Install

```
source .venv/bin/activate &&
pip install -r requirements.txt
```

## Docker Compose
- Spin up docker using `docker compose up`.
- This will create an ollama instance that will be used for the SLM.
- It will also create a FASTAPI endpoint `extract` that can be hit via the curl command below

## Usage

```
curl -X POST http://localhost:8000/extract \
  -H "Content-Type: application/json" \
  -d '{"prompt":"What time are the Knicks playing","url":"https://www.espn.com/nba/schedule"}'
```

