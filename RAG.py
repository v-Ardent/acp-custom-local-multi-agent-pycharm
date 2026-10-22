import chromadb

client = chromadb.PersistentClient(path="./memoire")
collection = client.get_or_create_collection("tools")

collection.add(
    ids=["m1", "m2", "m3"],
    documents=["Léa est végétarienne",
    "Léa code en Python 3.12",
    "Léa a adoré le curry de pois chiches"],
    metadatas=[{"source": "notion"}, {"source": "google-docs"}, {"source": "notion"}],)


def add_to_collection(document, collection_name:str, ids, metadatas=None):
    pass

def search_memory(txt, collection_name:str, metadata_field: dict[str, str] | None = None, regex=None):
    if not collection_name:
        raise ValueError("Collection name not provided")

    try:
        collection = client.get_collection(collection_name)
    except Exception as e:
        raise ValueError(f"Collection '{collection_name}' not found") from e

    return collection.query(
        query_texts=[txt],
        n_results=1,
        where=metadata_field,
        where_document={"$contains": regex},
    )