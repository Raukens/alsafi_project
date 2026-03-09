#!/usr/bin/env python3
"""
RAG-пайплайн для PDF: загрузка, чанкинг, индексация и ответы на вопросы.
Использует sentence-transformers для эмбеддингов (локально) и ChromaDB.
"""
import os
import re
import argparse
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()  # Загружает OPENAI_API_KEY из .env

from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
# from langchain_community.vectorstores import Chroma
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain_core.prompts import PromptTemplate
from langchain_classic.chains import RetrievalQA
from langchain_openai import ChatOpenAI

# Пути по умолчанию
BASE_DIR = Path(__file__).resolve().parent
CHROMA_PATH = BASE_DIR / "knowledge_base" / "chroma_db"
# Модель эмбеддингов (OpenAI — мультиязычная, лучше для русский↔английский)
EMBEDDING_MODEL = "text-embedding-3-small"


def _is_toc_page(doc) -> bool:
    """Определяет, похожа ли страница на оглавление (много строк с ..... номер)."""
    text = doc.page_content or ""
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    if len(lines) < 3:
        return False
    # Строки TOC: текст, точки, номер страницы
    toc_lines = sum(1 for l in lines if re.search(r"\.{2,}\s*\d+\s*$", l))
    return toc_lines / len(lines) > 0.25


def _make_qa_prompt():
    """Промпт: отвечать только на основе контекста, документ на английском."""
    return PromptTemplate(
        template="""Use the following context from an English regulatory document to answer the question.
If the answer is not in the context, say so. Do not invent information.
Synonyms: "large exposure" = "single obligor" = "concentration" = max risk per borrower.

Context:
{context}

Question: {question}

Answer (in the same language as the question):""",
        input_variables=["context", "question"],
    )


def load_and_chunk_pdf(pdf_path: str, chunk_size: int = 1000, chunk_overlap: int = 200, skip_toc: bool = True):
    """
    Загрузка PDF и разбиение на чанки.
    chunk_size=1000, chunk_overlap=200 — для регуляторных документов.
    skip_toc=True — исключает страницы оглавления (TOC).
    """
    loader = PyPDFLoader(pdf_path)
    pages = loader.load()

    if skip_toc:
        toc_pages = {doc.metadata.get("page", i) for i, doc in enumerate(pages) if _is_toc_page(doc)}
        pages = [p for i, p in enumerate(pages) if p.metadata.get("page", i) not in toc_pages]
        print(f"Пропущено {len(toc_pages)} страниц оглавления (TOC).")

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    chunks = text_splitter.split_documents(pages)
    print(f"Загружено {len(pages)} страниц, создано {len(chunks)} чанков.")
    return chunks


def ingest_pdf(pdf_path: str, collection_name: str = "pdf_docs"):
    """Загружает PDF, создаёт чанки и индексирует в ChromaDB."""
    if not Path(pdf_path).exists():
        raise FileNotFoundError(f"Файл не найден: {pdf_path}")

    embeddings = OpenAIEmbeddings(model=EMBEDDING_MODEL)
    chunks = load_and_chunk_pdf(pdf_path)

    CHROMA_PATH.mkdir(parents=True, exist_ok=True)
    Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory=str(CHROMA_PATH),
        collection_name=collection_name,
    )
    print(f"Индекс сохранён в {CHROMA_PATH}")


def ask_return(question: str, collection_name: str = "pdf_docs", model: str = "gpt-4o-mini"):
    """
    Ответ на вопрос по документу через RAG. Возвращает dict для API (Django и др.).
    Ключи: result (str), source_documents (list).
    """
    if not CHROMA_PATH.exists():
        return {"result": "Индекс документов не найден. Сначала выполните индексацию: python pdf_rag.py ingest <путь_к_pdf>", "source_documents": []}

    embeddings = OpenAIEmbeddings(model=EMBEDDING_MODEL)
    vectorstore = Chroma(
        persist_directory=str(CHROMA_PATH),
        embedding_function=embeddings,
        collection_name=collection_name,
    )
    llm = ChatOpenAI(model=model, temperature=0, api_key=os.environ.get("OPENAI_API_KEY"))
    qa_chain = RetrievalQA.from_chain_type(
        llm=llm,
        retriever=vectorstore.as_retriever(search_kwargs={"k": 8}),
        return_source_documents=True,
        chain_type_kwargs={"prompt": _make_qa_prompt()},
    )
    return qa_chain.invoke({"query": question})


def ask(question: str, collection_name: str = "pdf_docs", model: str = "gpt-4o-mini"):
    """Ответ на вопрос по документу через RAG (CLI: печать в консоль)."""
    result = ask_return(question, collection_name, model)
    print("\n--- Ответ ---\n")
    print(result["result"])
    if result.get("source_documents"):
        print("\n--- Источники ---")
        for i, doc in enumerate(result["source_documents"][:3], 1):
            print(f"{i}. стр. {doc.metadata.get('page', '?')}: {doc.page_content[:200]}...")


def main():
    parser = argparse.ArgumentParser(description="RAG по PDF: индексация и QA")
    subparsers = parser.add_subparsers(dest="command", required=True)

    ingest_parser = subparsers.add_parser("ingest", help="Загрузить PDF и создать индекс")
    ingest_parser.add_argument("pdf", help="Путь к PDF-файлу")
    ingest_parser.add_argument(
        "--collection",
        default="pdf_docs",
        help="Имя коллекции в ChromaDB (по умолчанию: pdf_docs)",
    )

    ask_parser = subparsers.add_parser("ask", help="Задать вопрос по документу")
    ask_parser.add_argument("question", help="Вопрос на английском")
    ask_parser.add_argument(
        "--collection",
        default="pdf_docs",
        help="Имя коллекции (по умолчанию: pdf_docs)",
    )
    ask_parser.add_argument(
        "--model",
        default="gpt-4o-mini",
        help="Модель OpenAI (по умолчанию: gpt-4o-mini)",
    )

    args = parser.parse_args()

    if args.command == "ingest":
        ingest_pdf(args.pdf, args.collection)
    elif args.command == "ask":
        ask(args.question, args.collection, args.model)


if __name__ == "__main__":
    main()

# ask_return("Какой норматив по капиталу?")