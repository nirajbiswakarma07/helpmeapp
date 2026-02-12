from django.db import models
import uuid


# Create your models here.

class QdrantCollection(models.Model):
    name = models.CharField(max_length=255, unique=True)
    embedding_model = models.CharField(max_length=100)
    vector_size = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Document(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    title = models.CharField(max_length=1000)
    file = models.FileField(upload_to="documents/")
    content_hash = models.CharField(max_length=128, unique=True)

    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


class DocumentCollection(models.Model):
    STATUS_CHOICES = (
        ("pending", "Pending"),
        ("processing", "Processing"),
        ("completed", "Completed"),
        ("failed", "Failed"),
    )

    document = models.ForeignKey(Document, on_delete=models.CASCADE)
    collection = models.ForeignKey(QdrantCollection, on_delete=models.CASCADE)

    qdrant_document_id = models.CharField(max_length=255)
    chunk_count = models.IntegerField(null=True, blank=True)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")

    uploaded_to_qdrant_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ("document", "collection")

    def __str__(self):
        return f"{self.document.title} → {self.collection.name}"

