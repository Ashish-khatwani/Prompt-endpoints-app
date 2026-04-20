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
- **NEW**: Individual endpoints for testing each prompt component separately
- Handles common empty states and failures with visible error messages

## API Endpoints

The backend provides the following endpoints:

### Core Endpoints
- `GET /health` - Health check
- `GET /documents` - List uploaded documents
- `POST /upload` - Upload a document for RAG
- `POST /retrieve` - Retrieve relevant context from uploaded documents
- `POST /assemble` - Assemble prompt sections into a formatted prompt
- `POST /generate` - Generate response using all prompt sections

### Individual Section Testing Endpoints
- `POST /generate/system-instructions` - Test system instructions only
- `POST /generate/user-input` - Test user input only
- `POST /generate/retrieved-knowledge` - Test retrieved knowledge only
- `POST /generate/state-and-memory` - Test state & memory only

### External/RAG Endpoints
- `POST /external/rag-chunks` - Retrieve RAG chunks (public)
- `POST /external/rag-response` - Generate response with RAG (public)

Each individual section endpoint accepts:
```json
{
  "content": "The content to test",
  "model": "optional-model-name",
  "temperature": 0.2
}
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

## Frontend Features

- **Separate Section Editing**: Edit each prompt component in its own textarea
- **Test Individual Sections**: Use "Test Section" buttons to generate responses using only system instructions, user input, retrieved knowledge, or state & memory
- **Full Prompt Assembly**: Combine all sections and preview the complete prompt
- **RAG Integration**: Upload documents and retrieve relevant context
- **Model Response Testing**: Send prompts to configured model API
- **Error Handling**: Clear error messages for failed operations

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
