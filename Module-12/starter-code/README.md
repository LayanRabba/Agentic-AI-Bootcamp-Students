# Module 12 — Memory Chat Agent (starter code)

A general chat agent with streaming WebSocket replies, short-term memory (compaction) and long-term memory (Chroma).

## Run locally

```bash
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env     # add your OpenRouter key
uvicorn app:app --port 8000
```

Open http://localhost:8000

## Run in Docker

```bash
docker buildx build --platform linux/amd64 -t chat-agent:latest --load .
docker run --rm -p 8000:8000 --env-file .env chat-agent:latest
```

## Endpoints

- `/` chat UI
- `/ws` WebSocket chat (streams tokens)
- `/health` liveness
- `/memory/stats` memory counters

## Configuration (`.env`)

See `.env.example`: API key, model, message length cap, requests per minute, compaction threshold.

## Deploy

See `../AWS-DEPLOYMENT-GUIDE.html`.
