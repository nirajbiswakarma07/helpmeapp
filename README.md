# RAG System with OCR and LLM (Django)

A **Retrieval-Augmented Generation (RAG)** system built with **Django**, **OpenAI LLM**, and **OCR support for scanned PDFs and images**.

This project allows users to upload documents (including scanned PDFs), extract text using OCR, store embeddings, and query the knowledge base using an LLM-powered retrieval system.

The system retrieves the most relevant context from documents and generates accurate answers using OpenAI models.

---

# Features

## RAG Pipeline
- Retrieval-Augmented Generation using document embeddings
- Context-aware answers from stored documents

## OCR Support
- Extracts text from scanned PDFs and images
- Uses **EasyOCR + OpenCV**

## Document Processing
- Upload PDFs and images
- Automatic text extraction and chunking

## Vector-Based Retrieval
- Stores document embeddings
- Retrieves the most relevant chunks for queries

## LLM Integration
- Uses OpenAI models to generate responses
- Context injection from retrieved documents

## Django Backend
- REST APIs for document upload and querying
- Modular and scalable backend architecture

## Containerized Deployment
- Docker support for easy deployment

---

# System Architecture

```
User Query
    │
    ▼
Embedding Generation
    │
    ▼
Vector Search
    │
    ▼
Relevant Context Retrieval
    │
    ▼
LLM (OpenAI)
    │
    ▼
Generated Answer
```

### Document Processing Pipeline

```
Upload Document
      │
      ▼
OCR (EasyOCR + OpenCV)
      │
      ▼
Text Extraction
      │
      ▼
Text Chunking
      │
      ▼
Embedding Generation
      │
      ▼
Vector Storage
```

---

# Tech Stack

### Backend
- Django
- Django REST Framework

### AI / ML
- OpenAI API
- Embeddings for semantic search

### OCR
- EasyOCR
- OpenCV
- Pillow

### Document Processing
- PDF parsing
- Image preprocessing

### Deployment
- Docker
- Docker Compose

---

# Installation

## Clone the Repository

```bash
git clone https://github.com/nirajbiswakarma07/helpmeapp.git
cd helpmeapp
```

---

## Create Environment Variables

Create a `.env` file:

```
OPENAI_API_KEY=your_openai_api_key
```

---

## Install Dependencies

Using pip:

```bash
pip install -r requirements.txt
```

Or using **uv**:

```bash
uv sync
```

---

## Run Migrations

```bash
python manage.py migrate
```

---

## Start the Server

```bash
python manage.py runserver
```

---

# Docker Setup

Build and run using Docker Compose:

```bash
docker compose up --build
```

Application will run at:

```
http://localhost:8000
```

---

# Project Structure

```
rag-project/
│
├── docker/
│   ├── Dockerfile
│   └── compose.yaml
│
├── app/
│   ├── models.py
│   ├── views.py
│   ├── services/
│   │   ├── rag_pipeline.py
│   │   ├── ocr_service.py
│   │   └── embedding_service.py
│
├── media/
│   └── uploaded_documents/
│
├── pyproject.toml
├── uv.lock
└── README.md
```

---

# API Workflow

## 1. Upload Document

Upload PDFs or images.

The system will:
- Extract text
- Perform OCR if needed
- Chunk the text
- Generate embeddings
- Store them for retrieval

---

## 2. Ask Questions

Send a query to the RAG system.

The system will:

1. Generate query embeddings  
2. Retrieve relevant document chunks  
3. Send context + question to OpenAI  
4. Return the generated answer  

---

# Example Use Cases

- Knowledge base assistants
- Document Q&A systems
- Internal company documentation search
- Legal document analysis
- Research paper querying

---

# Future Improvements

- Streaming LLM responses
- Support for multiple vector databases
- Semantic document indexing
- Authentication and user-based document access
- Frontend chat interface

---

# Author

**Niraj Biswakarma**

Full Stack Developer  
Django | AI Applications | RAG Systems