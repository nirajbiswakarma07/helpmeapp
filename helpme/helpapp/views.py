from django.db import transaction
from django.shortcuts import render, redirect, get_object_or_404
from django.utils.text import slugify
from django.contrib import messages
from django.utils import timezone
from django.conf import settings
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt

import hashlib
import os
import uuid
import io

import easyocr
import numpy as np
import cv2

easy_reader = easyocr.Reader(['en'], gpu=False)

from qdrant_client import QdrantClient
from qdrant_client.models import (
    VectorParams,
    Distance,
    PointStruct,
    FilterSelector,
    Filter,
    FieldCondition,
    MatchValue,
)
from openai import OpenAI

import fitz
from PIL import Image
import pytesseract

from .models import Document, DocumentCollection, QdrantCollection
from .embeddings import generate_embeddings


pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

client = QdrantClient(url=settings.QDRANT_URL)
llm_client = OpenAI(api_key=settings.OPENAI_API_KEY)
SESSION_UPLOAD_KEY = "session_uploaded_doc_collection_ids"


def home(request):
    return render(request, "helpapp/home.html", {"active_page": "home"})



def ask(request):
    collections = QdrantCollection.objects.order_by("name")
    qa_history = request.session.get("qa_history", [])

    context = {
        "active_page": "ask",
        "collections": collections,
        "selected_collection_id": "",
        "question": "",
        "qa_history": qa_history,
    }

    if request.method != "POST":
        request.session.pop("qa_history", None)
        context["qa_history"] = []
        return render(request, "helpapp/ask.html", context)

    selected_collection_id = request.POST.get("collection", "").strip()
    question = request.POST.get("question", "").strip()

    context["selected_collection_id"] = selected_collection_id
    context["question"] = question

    if not selected_collection_id or not question:
        messages.error(request, "Please select a collection and enter a question.")
        return render(request, "helpapp/ask.html", context)

    try:
        collection = QdrantCollection.objects.get(id=selected_collection_id)
    except QdrantCollection.DoesNotExist:
        messages.error(request, "Selected collection does not exist.")
        return render(request, "helpapp/ask.html", context)

    try:
        answer, sources = _answer_question_from_collection(collection, question)

        qa_history.insert(0, {
            "collection_name": collection.name,
            "question": question,
            "answer": answer,
            "sources": sources,
        })

        qa_history = qa_history[:20]
        request.session["qa_history"] = qa_history
        context["qa_history"] = qa_history
        context["question"] = ""

    except Exception as exc:
        messages.error(request, f"Unable to generate answer: {exc}")

    return render(request, "helpapp/ask.html", context)



def file_portal(request):
    if request.method == "POST":
        collection_id = request.POST.get("collection")
        uploaded_files = request.FILES.getlist("files")

        if not collection_id or not uploaded_files:
            messages.error(request, "Select collection and files.")
            return _render_file_portal(request)

        try:
            collection = QdrantCollection.objects.get(id=collection_id)
        except QdrantCollection.DoesNotExist:
            messages.error(request, "Collection does not exist.")
            return _render_file_portal(request)

        try:
            client.get_collection(collection.name)
        except:
            client.create_collection(
                collection_name=collection.name,
                vectors_config=VectorParams(
                    size=collection.vector_size,
                    distance=Distance.COSINE,
                ),
            )

        session_uploaded_ids = request.session.get(SESSION_UPLOAD_KEY, [])

        for uploaded_file in uploaded_files:
            file_hash = _hash_uploaded_file(uploaded_file)
            original_name = os.path.basename(uploaded_file.name)
            stored_name = f"collections/{slugify(collection.name)}/{original_name}"
            uploaded_file.name = stored_name

            with transaction.atomic():
                document, _ = Document.objects.get_or_create(
                    content_hash=file_hash,
                    defaults={"title": original_name, "file": uploaded_file},
                )

                doc_collection, created = DocumentCollection.objects.get_or_create(
                    document=document,
                    collection=collection,
                    defaults={
                        "qdrant_document_id": str(document.id),
                        "status": "processing",
                    },
                )

                if not created:
                    continue

                if doc_collection.id not in session_uploaded_ids:
                    session_uploaded_ids.append(doc_collection.id)

                pages = extract_text_from_file(document.file)

                points = []

                for page_number, page_text in pages:

                    chunk_size = 800
                    chunks = [
                        page_text[i:i + chunk_size]
                        for i in range(0, len(page_text), chunk_size)
                    ]

                    if not chunks:
                        continue

                    vectors = []
                    batch_size = 50

                    for i in range(0, len(chunks), batch_size):
                        batch = chunks[i:i + batch_size]
                        batch_vectors = generate_embeddings(
                            batch,
                            collection.embedding_model
                        )
                        vectors.extend(batch_vectors)

                    for i, (chunk, vector) in enumerate(zip(chunks, vectors)):
                        points.append(
                            PointStruct(
                                id=str(uuid.uuid4()),
                                vector=vector,
                                payload={
                                    "document_id": str(document.id),
                                    "document_title": document.title,
                                    "page_number": page_number,
                                    "text": chunk,
                                },
                            )
                        )

                if points:
                    client.upsert(
                        collection_name=collection.name,
                        points=points,
                    )

                doc_collection.status = "completed"
                doc_collection.uploaded_to_qdrant_at = timezone.now()
                doc_collection.save()

        request.session[SESSION_UPLOAD_KEY] = session_uploaded_ids

        messages.success(request, "Upload completed.")
        return redirect("file_portal")

    return _render_file_portal(request)


def delete_file(request, doc_collection_id):
    if request.method != "POST":
        return redirect("file_portal")

    doc_collection = get_object_or_404(
        DocumentCollection.objects.select_related("document", "collection"),
        id=doc_collection_id,
    )

    document = doc_collection.document
    collection = doc_collection.collection

    try:
        client.delete(
            collection_name=collection.name,
            points_selector=FilterSelector(
                filter=Filter(
                    must=[
                        FieldCondition(
                            key="document_id",
                            match=MatchValue(value=str(document.id)),
                        )
                    ]
                )
            ),
        )
    except Exception as exc:
        messages.warning(
            request,
            f"Removed DB link but could not fully delete points from Qdrant: {exc}",
        )

    doc_collection.delete()

    session_uploaded_ids = request.session.get(SESSION_UPLOAD_KEY, [])
    if doc_collection_id in session_uploaded_ids:
        session_uploaded_ids.remove(doc_collection_id)
        request.session[SESSION_UPLOAD_KEY] = session_uploaded_ids

    if not DocumentCollection.objects.filter(document=document).exists():
        document.file.delete(save=False)
        document.delete()

    messages.success(request, "File deleted and Qdrant points removed.")
    next_url = request.POST.get("next", "")
    if next_url.startswith("/"):
        return redirect(next_url)
    return redirect("file_portal")


def all_files(request):
    files = DocumentCollection.objects.select_related(
        "document", "collection"
    ).order_by("-document__uploaded_at")
    return render(
        request,
        "helpapp/all_files.html",
        {
            "active_page": "files",
            "files": files,
        },
    )


def extract_text_from_file(file):
    file_name = file.name.lower()

    if file_name.endswith(".txt"):
        content = file.read().decode("utf-8", errors="ignore")
        file.seek(0)
        return [(1, content)]

    elif file_name.endswith(".pdf"):
        pages = []
        pdf = fitz.open(stream=file.read(), filetype="pdf")

        for page_number, page in enumerate(pdf, start=1):
            text = page.get_text()

            if not text.strip():
                pix = page.get_pixmap()
                img = Image.open(io.BytesIO(pix.tobytes()))
                text = pytesseract.image_to_string(img)

            pages.append((page_number, text))

        file.seek(0)
        return pages

    elif file_name.endswith((".png", ".jpg", ".jpeg")):
        file_bytes = np.asarray(bytearray(file.read()), dtype=np.uint8)
        img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)

        scale_factor = 2.5
        img = cv2.resize(
            img,
            None,
            fx=scale_factor,
            fy=scale_factor,
            interpolation=cv2.INTER_CUBIC
        )
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        gray = cv2.bilateralFilter(gray, 11, 17, 17)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        gray = clahe.apply(gray)
        kernel = np.array([[0, -1, 0],
                        [-1, 5, -1],
                        [0, -1, 0]])
        gray = cv2.filter2D(gray, -1, kernel)
        results = easy_reader.readtext(gray, detail=0, paragraph=True)
        text = "\n".join(results)
        file.seek(0)
        return [(1, text)]

    file.seek(0)
    return []



from collections import defaultdict

def _answer_question_from_collection(collection, question):

    query_vector = generate_embeddings(
        [question],
        collection.embedding_model
    )[0]

    search_result = client.query_points(
        collection_name=collection.name,
        query=query_vector,
        limit=20,
    )

    hits = search_result.points

    if not hits:
        return "No relevant information found.", []

    doc_scores = defaultdict(float)
    doc_hits = defaultdict(list)

    for hit in hits:
        doc_id = hit.payload.get("document_id")
        score = hit.score or 0.0
        weighted_score = score ** 2
        doc_scores[doc_id] += weighted_score
        doc_hits[doc_id].append(hit)

    ranked_docs = sorted(doc_scores.items(), key=lambda x: x[1], reverse=True)

    for doc_id, _ in ranked_docs:
        filtered_hits = sorted(
            doc_hits[doc_id],
            key=lambda x: x.score,
            reverse=True
        )[:5]

        contexts = []
        sources = []

        for hit in filtered_hits:
            payload = hit.payload
            contexts.append(payload.get("text", ""))
            sources.append({
                "file": payload.get("document_title"),
                "page": payload.get("page_number"),
            })

        context_text = "\n\n".join(contexts)

        response = llm_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a strict document extraction assistant. "
                        "Locate the field relevant to the question and return the COMPLETE line value exactly as it appears in the context. "
                        "Do NOT shorten the answer. Do NOT correct spelling. Do NOT infer. "
                        "If the field is not present verbatim, reply: 'Not found in document'."
                    )
                },
                {
                    "role": "user",
                    "content": f"Context:\n{context_text}\n\nQuestion: {question}"
                },
            ],
        )

        raw_answer = response.choices[0].message.content.strip()
        answer_lower = raw_answer.lower()

        failure_phrases = [
            "not found",
            "does not contain",
            "not present",
            "no information",
            "cannot find",
        ]

        if not any(phrase in answer_lower for phrase in failure_phrases):
            return raw_answer, sources

    return "Not found in document.", []


def _hash_uploaded_file(uploaded_file):
    sha = hashlib.sha256()
    for chunk in uploaded_file.chunks():
        sha.update(chunk)
    uploaded_file.seek(0)
    return sha.hexdigest()


def _render_file_portal(request):
    session_uploaded_ids = request.session.get(SESSION_UPLOAD_KEY, [])

    files = DocumentCollection.objects.select_related(
        "document", "collection"
    ).filter(id__in=session_uploaded_ids).order_by("-document__uploaded_at")

    collections = QdrantCollection.objects.order_by("name")
    all_files_count = DocumentCollection.objects.count()

    return render(
        request,
        "helpapp/file_portal.html",
        {
            "active_page": "files",
            "files": files,
            "collections": collections,
            "all_files_count": all_files_count,
        },
    )


@csrf_exempt
def clear_file_session(request):
    request.session.pop(SESSION_UPLOAD_KEY, None)
    return HttpResponse(status=204)
