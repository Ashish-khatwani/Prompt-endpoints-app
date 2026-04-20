from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from openai import OpenAI

from .config import UPLOAD_DIR, settings
from .prompting import build_prompt
from .rag import SUPPORTED_EXTENSIONS, combine_retrieval_results, rag_store
from .schemas import (
    DocumentsResponse,
    GenerateRequest,
    GenerateResponse,
    PromptAssemblyRequest,
    PromptAssemblyResponse,
    RetrieveRequest,
    RetrieveResponse,
    SingleSectionGenerateRequest,
    UploadResponse,
)


app = FastAPI(
    title="Prompt Testing Harness API",
    version="1.0.0",
    description="Simple backend for assembling prompts, ingesting documents, retrieving context, and calling a model API.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/documents", response_model=DocumentsResponse)
def list_documents() -> DocumentsResponse:
    return DocumentsResponse(documents=rag_store.list_documents())


@app.post("/upload", response_model=UploadResponse)
async def upload_document(file: UploadFile = File(...)) -> UploadResponse:
    if not file.filename:
        raise HTTPException(status_code=400, detail="Please choose a file to upload.")

    original_name = Path(file.filename).name
    extension = Path(original_name).suffix.lower()
    if extension not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type. Supported types: {', '.join(sorted(SUPPORTED_EXTENSIONS))}.",
        )

    payload = await file.read()
    if not payload:
        raise HTTPException(status_code=400, detail="The uploaded file is empty.")
    if len(payload) > settings.max_upload_size_bytes:
        raise HTTPException(status_code=400, detail="The uploaded file exceeds the 10 MB size limit.")

    try:
        document_id, chunk_count = rag_store.ingest(original_name, file.content_type or "", payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover
        raise HTTPException(status_code=500, detail="The file could not be processed.") from exc

    safe_name = f"{document_id}_{original_name}"
    (UPLOAD_DIR / safe_name).write_bytes(payload)

    return UploadResponse(
        document_id=document_id,
        file_name=original_name,
        chunks_indexed=chunk_count,
        message="File uploaded and indexed successfully.",
    )


@app.post("/retrieve", response_model=RetrieveResponse)
def retrieve_context(request: RetrieveRequest) -> RetrieveResponse:
    results = rag_store.retrieve(request.query, request.top_k)
    if not results:
        return RetrieveResponse(
            results=[],
            combined_text="",
            message="No relevant retrieved knowledge was found for this query.",
        )

    combined_text = combine_retrieval_results(results)
    return RetrieveResponse(
        results=results,
        combined_text=combined_text,
        message=f"Retrieved {len(results)} relevant chunk(s).",
    )

# --- Public endpoints for external app ---
from fastapi import Body
from .schemas import RetrieveRequest, GenerateRequest

@app.post("/external/rag-chunks", response_model=RetrieveResponse)
def external_rag_chunks(request: RetrieveRequest = Body(...)):
    """Return the retrieved RAG chunks and combined text for a query (public endpoint)."""
    results = rag_store.retrieve(request.query, request.top_k)
    if not results:
        return RetrieveResponse(
            results=[],
            combined_text="",
            message="No relevant retrieved knowledge was found for this query.",
        )
    combined_text = combine_retrieval_results(results)
    return RetrieveResponse(
        results=results,
        combined_text=combined_text,
        message=f"Retrieved {len(results)} relevant chunk(s).",
    )

@app.post("/external/rag-response", response_model=GenerateResponse)
def external_rag_response(request: GenerateRequest = Body(...)):
    """Return only the final RAG response for a prompt (public endpoint)."""
    prompt, _ = build_prompt(
        sections=request.sections,
        include_retrieved_knowledge=request.include_retrieved_knowledge,
    )
    if not settings.openai_api_key:
        raise HTTPException(
            status_code=500,
            detail="OPENAI_API_KEY is not configured on the backend. Add it to backend/.env before generating.",
        )
    client = OpenAI(api_key=settings.openai_api_key)
    model_name = request.model or settings.openai_model
    try:
        response = client.responses.create(
            model=model_name,
            input=prompt,
            temperature=request.temperature,
        )
        output_text = response.output_text or "The model returned an empty response."
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Model API call failed: {exc}") from exc
    return GenerateResponse(
        prompt=prompt,
        output_text=output_text,
        model_used=model_name,
    )


@app.post("/assemble", response_model=PromptAssemblyResponse)
def assemble_prompt(request: PromptAssemblyRequest) -> PromptAssemblyResponse:
    prompt, included_sections = build_prompt(
        sections=request.sections,
        include_retrieved_knowledge=request.include_retrieved_knowledge,
    )
    return PromptAssemblyResponse(prompt=prompt, included_sections=included_sections)


@app.post("/generate", response_model=GenerateResponse)
def generate_output(request: GenerateRequest) -> GenerateResponse:
    prompt, _ = build_prompt(
        sections=request.sections,
        include_retrieved_knowledge=request.include_retrieved_knowledge,
    )

    if not settings.openai_api_key:
        raise HTTPException(
            status_code=500,
            detail="OPENAI_API_KEY is not configured on the backend. Add it to backend/.env before generating.",
        )

    client = OpenAI(api_key=settings.openai_api_key)
    model_name = request.model or settings.openai_model

    try:
        response = client.responses.create(
            model=model_name,
            input=prompt,
            temperature=request.temperature,
        )
        output_text = response.output_text or "The model returned an empty response."
    except Exception as exc:  # pragma: no cover
        raise HTTPException(status_code=502, detail=f"Model API call failed: {exc}") from exc

    return GenerateResponse(
        prompt=prompt,
        output_text=output_text,
        model_used=model_name,
    )


@app.post("/generate/system-instructions", response_model=GenerateResponse)
def generate_system_instructions(request: SingleSectionGenerateRequest) -> GenerateResponse:
    prompt = f"System Instructions\n===================\n{request.content}"

    if not settings.openai_api_key:
        raise HTTPException(
            status_code=500,
            detail="OPENAI_API_KEY is not configured on the backend. Add it to backend/.env before generating.",
        )

    client = OpenAI(api_key=settings.openai_api_key)
    model_name = request.model or settings.openai_model

    try:
        response = client.responses.create(
            model=model_name,
            input=prompt,
            temperature=request.temperature,
        )
        output_text = response.output_text or "The model returned an empty response."
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Model API call failed: {exc}") from exc

    return GenerateResponse(
        prompt=prompt,
        output_text=output_text,
        model_used=model_name,
    )


@app.post("/generate/user-input", response_model=GenerateResponse)
def generate_user_input(request: SingleSectionGenerateRequest) -> GenerateResponse:
    prompt = f"Current User Input\n==================\n{request.content}"

    if not settings.openai_api_key:
        raise HTTPException(
            status_code=500,
            detail="OPENAI_API_KEY is not configured on the backend. Add it to backend/.env before generating.",
        )

    client = OpenAI(api_key=settings.openai_api_key)
    model_name = request.model or settings.openai_model

    try:
        response = client.responses.create(
            model=model_name,
            input=prompt,
            temperature=request.temperature,
        )
        output_text = response.output_text or "The model returned an empty response."
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Model API call failed: {exc}") from exc

    return GenerateResponse(
        prompt=prompt,
        output_text=output_text,
        model_used=model_name,
    )


@app.post("/generate/retrieved-knowledge", response_model=GenerateResponse)
def generate_retrieved_knowledge(request: SingleSectionGenerateRequest) -> GenerateResponse:
    prompt = f"Retrieved Knowledge\n===================\n{request.content}"

    if not settings.openai_api_key:
        raise HTTPException(
            status_code=500,
            detail="OPENAI_API_KEY is not configured on the backend. Add it to backend/.env before generating.",
        )

    client = OpenAI(api_key=settings.openai_api_key)
    model_name = request.model or settings.openai_model

    try:
        response = client.responses.create(
            model=model_name,
            input=prompt,
            temperature=request.temperature,
        )
        output_text = response.output_text or "The model returned an empty response."
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Model API call failed: {exc}") from exc

    return GenerateResponse(
        prompt=prompt,
        output_text=output_text,
        model_used=model_name,
    )


@app.post("/generate/state-and-memory", response_model=GenerateResponse)
def generate_state_and_memory(request: SingleSectionGenerateRequest) -> GenerateResponse:
    prompt = f"State & Memory\n==============\n{request.content}"

    if not settings.openai_api_key:
        raise HTTPException(
            status_code=500,
            detail="OPENAI_API_KEY is not configured on the backend. Add it to backend/.env before generating.",
        )

    client = OpenAI(api_key=settings.openai_api_key)
    model_name = request.model or settings.openai_model

    try:
        response = client.responses.create(
            model=model_name,
            input=prompt,
            temperature=request.temperature,
        )
        output_text = response.output_text or "The model returned an empty response."
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Model API call failed: {exc}") from exc

    return GenerateResponse(
        prompt=prompt,
        output_text=output_text,
        model_used=model_name,
    )
