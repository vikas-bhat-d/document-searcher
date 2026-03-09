import os
from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance
from langchain_ollama import OllamaEmbeddings

from config import *
from md_chunker import chunk_markdown

client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)

embeddings = OllamaEmbeddings(model=EMBED_MODEL)


def create_collection():

    if COLLECTION_NAME not in [c.name for c in client.get_collections().collections]:

        client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(
                size=768,
                distance=Distance.COSINE
            )
        )


def ingest_documents(folder):

    points = []
    idx = 0

    for file in os.listdir(folder):

        if not file.endswith(".md"):
            continue

        path = os.path.join(folder, file)

        with open(path, "r", encoding="utf-8") as f:
            text = f.read()

        chunks = chunk_markdown(text)
        print(chunks)

        vectors = embeddings.embed_documents(chunks)

        for chunk, vector in zip(chunks, vectors):

            points.append({
                "id": idx,
                "vector": vector,
                "payload": {
                    "document": file,
                    "text": chunk,
                    "chunk_id": idx
                }
            })

            idx += 1

    client.upsert(
        collection_name=COLLECTION_NAME,
        points=points
    )


if __name__ == "__main__":

    create_collection()

    ingest_documents("data/docs")

    print("Ingestion complete.")