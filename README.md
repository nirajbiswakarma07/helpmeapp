# HelpApp RAG (Django + OpenAI + Qdrant)

HelpApp is a Django-based document Q&A system. You upload files into a named Qdrant collection, the app extracts text, chunks it, generates embeddings with OpenAI, stores vectors in Qdrant, and answers questions grounded in the selected collection.

## What This Project Does

- Upload documents to a selected collection from a Files portal
- Extract text from `TXT`, `PDF`, and `PNG/JPG/JPEG`
- Create embeddings using OpenAI embedding models
- Store and search vectors in Qdrant
- Ask questions against one collection at a time using retrieval + `gpt-4o-mini`
- Show source file/page references with answers
- Delete a file and remove its associated vectors from Qdrant

## Tech Stack

- Python 3.10+
- Django 5.2
- OpenAI Python SDK
- Qdrant
- EasyOCR, OpenCV, PyMuPDF, Pillow, pytesseract
- `uv` for dependency management
- Docker (optional)

## Repository Layout

```text
.
|-- Dockerfile
|-- pyproject.toml
|-- README.md
`-- helpme/
    |-- manage.py
    |-- docker-compose.yml      # Qdrant service
    |-- db.sqlite3
    |-- media/
    |-- helpme/                 # Django project config
    `-- helpapp/                # Main app (views/models/templates/static)
```

## Prerequisites

Install these before running locally:

1. Python 3.10+
2. `uv` (`pip install uv`)
3. Qdrant (Docker recommended)
4. Tesseract OCR engine
5. OpenAI API key

## Environment Variables

Create `.env` in the repository root:

```env
OPENAI_API_KEY="your_openai_api_key"
```

Notes:

- `OPENAI_API_KEY` is required at startup (`helpme/helpme/settings.py` reads it via `python-decouple`).
- Qdrant URL is currently hardcoded in settings as `http://localhost:6333`.

## Local Development Setup

From repo root (`RAG/`):

```bash
uv sync
cd helpme
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

App URL: `http://127.0.0.1:8000/`
Admin URL: `http://127.0.0.1:8000/admin/`

## Start Qdrant (Docker Compose)

The compose file for Qdrant is at `helpme/docker-compose.yml`.

```bash
cd helpme
docker compose up -d
```

Qdrant endpoints:

- `http://localhost:6333` (HTTP)
- `localhost:6334` (gRPC)

## Create Collections (Required Before Upload)

Uploads require an existing `QdrantCollection` record in Django.

1. Open Django admin (`/admin`)
2. Create a `QdrantCollection`
3. Set `name` as the Qdrant collection name
4. Set `embedding_model` (example: `text-embedding-3-small`)
5. Set `vector_size` to the model dimension (example: `1536` for `text-embedding-3-small`)

If `vector_size` and model output dimension do not match, uploads will fail when writing vectors.

## How To Use

1. Go to **Files**
2. Select a collection
3. Upload one or more supported files
4. After upload completes, go to **Ask**
5. Pick the same collection and ask a question
6. Review answer + source file/page references

## URL Routes

- `/` -> Home
- `/files/` -> Upload/search current session files
- `/files/all/` -> All uploaded files
- `/files/delete/<doc_collection_id>/` -> Delete file + vectors (POST)
- `/files/session/clear/` -> Clear session upload list
- `/ask/` -> Collection-scoped Q&A
- `/admin/` -> Django admin

## Docker App Container (Optional)

Build and run from repo root:

```bash
docker build -t helpapp-rag .
docker run --rm -p 8000:8000 --env-file .env helpapp-rag
```

Important:

- The container expects Qdrant reachable at `http://localhost:6333` (current settings). In containerized setups, this usually needs to be changed to a service hostname.
- `views.py` sets a Windows-specific Tesseract path:
  `C:\Program Files\Tesseract-OCR\tesseract.exe`
  This must be adjusted for Linux containers if OCR is needed inside Docker.

## OCR and File Extraction Notes

- PDF flow uses direct text extraction first, then falls back to `pytesseract` when page text is empty
- Image flow uses OpenCV preprocessing and EasyOCR for improved recognition
- Text is chunked in ~800-character chunks before embedding
- Frontend filters show extra extensions (`docx`, `csv`, etc.), but backend extraction is currently implemented for `txt`, `pdf`, `png`, `jpg`, `jpeg`

## Known Limitations

- `SECRET_KEY` is hardcoded and `DEBUG=True` in `settings.py` (not production-safe)
- `ALLOWED_HOSTS` is empty
- No background worker; large uploads run in request/response cycle
- Qdrant URL is static in settings
- Tesseract executable path is OS-specific in code

## Troubleshooting

- `OPENAI_API_KEY` missing: add it to `.env` at repo root
- `No collections available` on Files/Ask pages: create `QdrantCollection` entries in admin first
- Upload succeeds but poor answers: verify OCR quality, use clean/high-resolution documents, and query the same collection used for upload
- Qdrant connection issues: confirm Qdrant is running on `localhost:6333`

## Security and Production Notes

Before production deployment:

1. Move sensitive settings (`SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS`, `QDRANT_URL`) to environment variables
2. Remove hardcoded Tesseract path or configure by environment
3. Add proper static/media serving strategy
4. Consider async/background processing for ingestion
5. Add tests for ingestion and retrieval flows
