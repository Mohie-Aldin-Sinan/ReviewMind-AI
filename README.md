# ReviewMind AI

Mobile app review intelligence for startup founders and small product teams.

ReviewMind AI is a product analytics tool that helps app teams turn user reviews into clear product priorities. The project focuses on importing mobile app reviews, identifying recurring customer issues, and producing a next-release action plan backed by evidence from real user feedback.

## Planned Scope

- Import reviews from Google Play, CSV, Excel, and pasted feedback
- Clean noisy review text before analysis
- Group reviews into mobile-app issue categories
- Extract bugs, feature requests, complaints, and positive feedback
- Rank priorities using RICE scoring
- Generate a next-release plan for small app teams

## Project Structure

```text
reviewmind-ai/
  backend/
  frontend/
  datasets/
```

## Status

Frontend dashboard supports pasted reviews and CSV upload for the local analysis workflow.

## Run Frontend

Start the backend, then open `frontend/index.html` in a browser. The dashboard sends pasted reviews and CSV uploads to the local FastAPI API at `http://127.0.0.1:8000`.

## Run Backend

```bash
cd backend
python -m pip install -r requirements.txt
python dev_server.py
```

Health check:

```text
http://127.0.0.1:8000/api/health
```

Import endpoints:

```text
POST /api/import/csv
POST /api/import/paste
```

Analysis endpoint:

```text
POST /api/analyze
```

Prioritization endpoint:

```text
POST /api/prioritize
```
