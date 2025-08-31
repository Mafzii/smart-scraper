# Smart Scraper

Smart Scraper is a simple tool for extracting data from websites.

## Usage

```
curl -X POST http://localhost:8000/extract \
  -H "Content-Type: application/json" \
  -d '{"prompt":"What time are the Knicks playing","url":"https://www.espn.com/nba/schedule"}'
```

