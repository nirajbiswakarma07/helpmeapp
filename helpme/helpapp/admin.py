from django.contrib import admin

from .models import QdrantCollection,Document,DocumentCollection

# Register your models here.
admin.site.register(QdrantCollection)
admin.site.register(Document)
admin.site.register(DocumentCollection)
