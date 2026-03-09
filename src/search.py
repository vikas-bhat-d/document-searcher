from qdrant_client import QdrantClient
from langchain_ollama import OllamaEmbeddings
from config import *

client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)

embeddings = OllamaEmbeddings(model=EMBED_MODEL)


def search(query, k=3):

    vector = embeddings.embed_query(query)

    hits = client.query_points(
        collection_name=COLLECTION_NAME,
        query=vector,
        limit=k
    ).points

    for h in hits:

        payload = h.payload

        print("\n---")
        print("Document:", payload["document"])
        print("Chunk:", payload["chunk_id"])
        print(payload["text"])


if __name__ == "__main__":

    while True:

        q = input("\nQuery: ")

        if q == "exit":
            break

        search(q)