import os
from typing import List, Set

from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import CharacterTextSplitter
from langchain_chroma import Chroma
from langchain_community.document_loaders import TextLoader, PyPDFLoader
from langchain_core.documents import Document

if __name__ == "__main__":
    print("Ingesting text file...")
    total_docs = 0
    total_files = 0
    base_directory = "knowledge_docs"
    documents: List[Document] = []
    current_files: Set[str] = set()  # Track current files

    # Initialize embeddings
    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2"
    )
    
    # Load existing vector store if it exists
    persist_directory = "data/cisco_products_custom_loader"
    if os.path.exists(persist_directory):
        print("Loading existing vector store...")
        vector_store = Chroma(
            collection_name="cisco_products_custom_loader",
            persist_directory=persist_directory,
            embedding_function=embeddings,
        )
        
        # Get all existing document sources from the store
        try:
            existing_collection = vector_store._collection
            existing_docs = existing_collection.get()
            existing_sources = set()
            if existing_docs and 'metadatas' in existing_docs:
                for metadata in existing_docs['metadatas']:
                    if metadata and 'source' in metadata:
                        existing_sources.add(metadata['source'])
            print(f"Found {len(existing_sources)} documents in existing vector store")
        except Exception as e:
            print(f"Could not load existing documents: {e}")
            existing_sources = set()
    else:
        print("No existing vector store found, will create new one")
        vector_store = None
        existing_sources = set()

    # Scan and load current files
    for root, dirs, files in os.walk(base_directory):
        # loop through dirs, each dir is a product, add that as metadata label for product then loop through files
        for dir in dirs:
            product = dir
            product_dir = os.path.join(base_directory, dir)
            for product_root, product_dirs, product_files in os.walk(product_dir):
                for file in product_files:
                    if file.endswith(".md") or file.endswith(".pdf"):
                        total_files += 1
                        full_path = os.path.join(product_root, file)
                        current_files.add(full_path)  # Track this file
                        
                        # Only process files that are NEW (not already in database)
                        if full_path in existing_sources:
                            print(f"Skipping (already in DB): {full_path}")
                            continue
                            
                        print(f"Reading file: {full_path}")
                        
                        # Use appropriate loader based on file type
                        if file.endswith(".pdf"):
                            loader = PyPDFLoader(full_path)
                        else:
                            loader = TextLoader(full_path)
                        
                        docs = loader.load()
                        print("Chunking it...")
                        text_splitter = CharacterTextSplitter(
                            chunk_size=1000, chunk_overlap=100
                        )
                        texts = text_splitter.split_documents(docs)
                        print(f"created {len(texts)} chunks")
                        # add metadata to each document
                        for doc in docs:
                            doc.metadata["product"] = product
                            doc.metadata["source"] = full_path

                        total_docs += len(docs)
                        documents.extend(docs)

    # Find files that were deleted (exist in DB but not in filesystem)
    deleted_sources = existing_sources - current_files
    if deleted_sources:
        print(f"\n🗑️  Found {len(deleted_sources)} deleted files to remove from database:")
        for source in deleted_sources:
            print(f"  - {source}")
        
        # Delete documents from deleted files
        if vector_store:
            for source in deleted_sources:
                try:
                    # Delete all documents with this source
                    vector_store._collection.delete(
                        where={"source": source}
                    )
                    print(f"  ✓ Removed: {source}")
                except Exception as e:
                    print(f"  ✗ Error removing {source}: {e}")
    else:
        print("\n✓ No deleted files to remove")

    # documents = filter_complex_metadata(documents)

    print("\nembedding documents...")
    print("Ingesting embeddings into vector store...")
    
    if vector_store is None:
        # Create new vector store
        vector_store = Chroma.from_documents(
            collection_name="cisco_products_custom_loader",
            persist_directory=persist_directory,
            embedding=embeddings,
            documents=documents,
        )
    else:
        # Add documents to existing store in batches to avoid exceeding max batch size
        batch_size = 5000
        for i in range(0, len(documents), batch_size):
            batch = documents[i:i + batch_size]
            vector_store.add_documents(batch)
            print(f"  Added batch {i//batch_size + 1}: {len(batch)} documents")
    
    print(f"\n✓ Finish!")
    print(f"  Total files scanned: {total_files}")
    print(f"  New files added: {len(documents) // max(1, total_docs) if total_docs > 0 else 0}")
    print(f"  New documents created: {total_docs}")
    print(f"  Files deleted from DB: {len(deleted_sources)}")
    print(f"  Files already in DB (skipped): {len(existing_sources & current_files)}")


