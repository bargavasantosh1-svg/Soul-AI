# SOUL

SOUL is my personal AI assistant (Python + FastAPI + HTML/CSS/JS).

## Start SOUL

1. Open the `Soul AI` folder in VS Code and open a terminal.
2. Activate the virtual environment:
   ```
   .venv\Scripts\activate
   ```
   You should see `(.venv)` at the start of the line.
3. Start the server:
   ```
   python -m uvicorn backend.main:app --reload
   ```
4. Open http://127.0.0.1:8000/ in the browser.

## Useful pages

- Chat page: http://127.0.0.1:8000/
- Health check: http://127.0.0.1:8000/api/health
- API test page: http://127.0.0.1:8000/docs

## Install packages

Always use `python -m pip install ...` (pip.exe is blocked on this laptop).

## Settings

All settings live in the `.env` file. Never share this file or paste the key anywhere.
Copy `.env.example` to make a new one.

## If something breaks

- Look at `logs/soul.log` (the last 20 lines).
- "Model not available" means Gemini renamed the model. Change only `OPENAI_MODEL` in `.env`.