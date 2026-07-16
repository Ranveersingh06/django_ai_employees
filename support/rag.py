import os
import chromadb
from pypdf import PdfReader
from chromadb.utils.embedding_functions import DefaultEmbeddingFunction


# Initialize ChromaDB
client = chromadb.PersistentClient(path="./chromadb")

embedding_fn = DefaultEmbeddingFunction()

collection = client.get_or_create_collection(
    name="coolbreeze_docs",
    embedding_function=embedding_fn,
)


def chunk_text(text, chunk_size=500):
    words = text.split()

    chunks = []
    current_chunk = []
    current_size = 0

    for word in words:
        current_chunk.append(word)
        current_size += len(word) + 1

        if current_size >= chunk_size:
            chunks.append(" ".join(current_chunk))
            current_chunk = []
            current_size = 0

    if current_chunk:
        chunks.append(" ".join(current_chunk))

    return chunks


def load_documents():

    docs_path = "support/documents"

    if not os.path.exists(docs_path):
        print(f"Documents folder not found: {docs_path}")
        return

    documents = []
    ids = []

    for filename in os.listdir(docs_path):

        if not filename.endswith(".pdf"):
            continue

        filepath = os.path.join(docs_path, filename)

        print(f"Loading: {filename}")

        reader = PdfReader(filepath)

        raw_text = ""

        for page in reader.pages:
            text = page.extract_text()

            if text:
                raw_text += text + "\n"

        if not raw_text.strip():
            print(f"No text extracted from {filename}")
            continue

        chunks = chunk_text(raw_text)

        for i, chunk in enumerate(chunks):
            documents.append(chunk)
            ids.append(f"{filename}_{i}")

    if not documents:
        print("No document chunks found.")
        return

    # Prevent duplicate inserts
    if collection.count() == 0:
        collection.add(
            documents=documents,
            ids=ids,
        )
        print(f"Loaded {len(documents)} chunks into ChromaDB.")
    else:
        print("Collection already contains documents.")

    print("Collection Count:", collection.count())


def search_knowledge_base(query):

    print("Searching for:", query)

    print("Collection Count:", collection.count())

    results = collection.query(
        query_texts=[query],
        n_results=3,
    )

    print("DEBUG RESULTS:", results["documents"])

    if not results["documents"] or not results["documents"][0]:
        return "No relevant information found in company documents."

    matched_chunks = results["documents"][0]

    return "\n\n".join(matched_chunks)