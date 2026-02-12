from openai import OpenAI
from django.conf import settings

client = OpenAI(api_key=settings.OPENAI_API_KEY)

EMBEDDING_MODEL = "text-embedding-3-small"


def generate_embeddings(text_chunks, model_name):
    response = client.embeddings.create(
        model=model_name,
        input=text_chunks,
    )
    return [item.embedding for item in response.data]
