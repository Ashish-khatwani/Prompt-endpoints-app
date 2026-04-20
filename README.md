# Prompt Testing Harness

A minimal full-stack prompt testing application built with:

- `frontend/`: Vite + React
- `backend/`: FastAPI + Python

It is designed to help inspect and test prompt components before sending the final prompt to a real model API.

## What It Does

- Keeps prompt components separate and editable:
  - System Instructions
  - User Input
  - Conversation History
  - Retrieved Knowledge
  - Tool Definitions
  - State & Memory
- Assembles those sections into a final structured prompt preview
- Supports simple file-based RAG for `txt`, `md`, `pdf`, `docx`, `json`, and `csv`
- Calls a real model API from the backend
- Handles common empty states and failures with visible error messages

## Project Structure

```text
backend/
  app/
    config.py
    main.py
    prompting.py
    rag.py
    schemas.py
  requirements.txt
  .env.example

frontend/
  src/
    api.js
    App.jsx
    main.jsx
    styles.css
  index.html
  package.json
  vite.config.js
```

## Backend Setup

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

Add your API key to `backend/.env`:

```env
OPENAI_API_KEY=your_api_key_here
OPENAI_MODEL=gpt-4.1-mini
```

Run the backend:

```bash
uvicorn app.main:app --reload
```

The API runs on `http://localhost:8000`.

## Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

The UI runs on `http://localhost:5173`.

If needed, set a custom backend URL:

```bash
set VITE_API_BASE_URL=http://localhost:8000
```

## Simple RAG Behavior

- Uploaded files are parsed on the backend
- Extracted text is chunked into overlapping text slices
- Retrieval uses a lightweight token-overlap search
- Retrieved chunks are shown in the UI and copied into the `Retrieved Knowledge` field
- The user can choose whether to include retrieved knowledge in the final prompt

## Reliability Notes

- Empty inputs do not crash the app
- Empty uploads and unsupported file types return clear errors
- Retrieval gracefully reports when no useful match is found
- Model API errors are surfaced to the UI
- Long text is displayed in scrollable panels and preserved in the backend flow

## Future Enhancements

Optional improvements if you want to extend this later:

- persistent document metadata/index storage
- document deletion
- retrieval highlighting
- prompt templates / saved test cases
- automated side-by-side prompt experiments
