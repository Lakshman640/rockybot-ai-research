import os
import time
import json
from urllib.parse import urlparse
from typing import List
from pydantic import BaseModel
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from dotenv import load_dotenv

# Ensure environment variables are loaded
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
env_file = os.path.join(BASE_DIR, ".env")
if os.path.exists(env_file):
    load_dotenv(env_file)
else:
    load_dotenv()

api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
if api_key:
    os.environ["GOOGLE_API_KEY"] = api_key
    os.environ["GEMINI_API_KEY"] = api_key

# LangChain Imports
from langchain_core.prompts import PromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
try:
    from langchain_classic.chains import RetrievalQAWithSourcesChain
except ImportError:
    from langchain.chains import RetrievalQAWithSourcesChain  # type: ignore[import-not-found]

from langchain_community.document_loaders import WebBaseLoader
from langchain_community.vectorstores import FAISS
from langchain_text_splitters import RecursiveCharacterTextSplitter

app = FastAPI(title="RockyBot AI API", description="AI News & Financial Research Engine", version="2.0.0")

# Enable CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

INDEX_DIR = os.path.join(BASE_DIR, "faiss_store_gemini")
METADATA_FILE = os.path.join(INDEX_DIR, "sources_metadata.json")

import re
from langchain_core.embeddings import Embeddings

class ThrottledGoogleEmbeddings(Embeddings):
    """Wraps Google embeddings with batching and automatic retry on 429 rate limits."""
    def __init__(self, base_embeddings, batch_size=15, delay_between_batches=0.6, max_retries=3):
        self.base = base_embeddings
        self.batch_size = batch_size
        self.delay_between_batches = delay_between_batches
        self.max_retries = max_retries

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        all_embeddings = []
        total = len(texts)
        for i in range(0, total, self.batch_size):
            batch = texts[i : i + self.batch_size]
            for attempt in range(self.max_retries):
                try:
                    res = self.base.embed_documents(batch)
                    all_embeddings.extend(res)
                    break
                except Exception as e:
                    err_msg = str(e)
                    if "429" in err_msg or "RESOURCE_EXHAUSTED" in err_msg:
                        delay = 16.0
                        match = re.search(r"retryDelay['\"]?:\s*['\"]?([\d\.]+)s", err_msg)
                        if match:
                            try:
                                delay = float(match.group(1)) + 1.5
                            except Exception:
                                delay = 16.0
                        if attempt < self.max_retries - 1:
                            print(f"[Embedding Rate Limit] 429 received. Pausing {delay:.1f}s before retry attempt {attempt + 2}/{self.max_retries}...")
                            time.sleep(delay)
                            continue
                    raise e
            if i + self.batch_size < total:
                time.sleep(self.delay_between_batches)
        return all_embeddings

    def embed_query(self, text: str) -> List[float]:
        for attempt in range(self.max_retries):
            try:
                return self.base.embed_query(text)
            except Exception as e:
                err_msg = str(e)
                if ("429" in err_msg or "RESOURCE_EXHAUSTED" in err_msg) and attempt < self.max_retries - 1:
                    time.sleep(16.0)
                    continue
                raise e

# Helpers for models
def get_embeddings():
    key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    if not key:
        raise ValueError("GOOGLE_API_KEY is not configured in .env")
    base_emb = GoogleGenerativeAIEmbeddings(
        model="gemini-embedding-2",
        output_dimensionality=1536,
        google_api_key=key
    )
    return ThrottledGoogleEmbeddings(base_emb, batch_size=15, delay_between_batches=0.6)

def get_llm():
    key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    if not key:
        raise ValueError("GOOGLE_API_KEY is not configured in .env")
    return ChatGoogleGenerativeAI(
        model="gemini-flash-lite-latest",
        temperature=0.2,
        max_output_tokens=700,
        google_api_key=key
    )

def is_informative_content(text: str) -> tuple[bool, str]:
    """Validates whether extracted webpage content contains actual article text."""
    cleaned = text.strip()
    if len(cleaned) < 200:
        return False, f"Extracted content is too short ({len(cleaned)} characters)."

    blocked_indicators = [
        "please enable js",
        "disable any ad blocker",
        "enable javascript",
        "access denied",
        "captcha",
        "bot detection",
        "security check",
        "403 forbidden",
        "just a moment..."
    ]
    lower = cleaned.lower()
    for phrase in blocked_indicators:
        if phrase in lower and len(cleaned) < 1500:
            return False, f"Automated extraction blocked by website ('{phrase}' detected)."

    return True, ""

def save_sources_metadata(urls: List[str], chunk_count: int):
    os.makedirs(INDEX_DIR, exist_ok=True)
    sources = []
    for u in urls:
        domain = urlparse(u).netloc or "web"
        sources.append({
            "url": u,
            "domain": domain,
            "added_at": time.strftime("%Y-%m-%d %H:%M:%S")
        })
    data = {
        "sources": sources,
        "chunk_count": chunk_count,
        "updated_at": time.strftime("%Y-%m-%d %H:%M:%S")
    }
    with open(METADATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def load_sources_metadata():
    if os.path.exists(METADATA_FILE):
        try:
            with open(METADATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return None

# Request & Response Models
class ProcessURLsRequest(BaseModel):
    urls: List[str]

class QueryRequest(BaseModel):
    question: str

@app.get("/api/status")
def get_status():
    key_configured = bool(os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY"))
    index_exists = os.path.exists(os.path.join(INDEX_DIR, "index.faiss"))
    meta = load_sources_metadata() if index_exists else None
    return {
        "api_key_configured": key_configured,
        "index_ready": index_exists,
        "metadata": meta
    }

@app.post("/api/process-urls")
def process_urls(req: ProcessURLsRequest):
    key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    if not key:
        raise HTTPException(status_code=400, detail="Google API Key missing. Please configure .env file.")

    # Filter non-empty valid URLs - works seamlessly even for 1 single URL!
    valid_urls = [u.strip() for u in req.urls if u and u.strip()]
    if not valid_urls:
        raise HTTPException(status_code=400, detail="Please provide at least one valid URL.")

    extracted_docs = []
    failed_urls = []

    for url in valid_urls:
        try:
            loader = WebBaseLoader(
                url,
                header_template={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                }
            )
            loaded = loader.load()
            if not loaded or not loaded[0].page_content.strip():
                failed_urls.append({"url": url, "reason": "No readable content returned from page."})
                continue

            doc = loaded[0]
            doc.metadata["source"] = url
            is_valid, reason = is_informative_content(doc.page_content)
            if not is_valid:
                failed_urls.append({"url": url, "reason": reason})
            else:
                extracted_docs.append(doc)
        except Exception as e:
            failed_urls.append({"url": url, "reason": f"Fetch error: {str(e)}"})

    if not extracted_docs:
        detail_msg = "Could not extract readable article content from the URL(s) provided."
        if failed_urls:
            reasons = "; ".join([f"{f['url']}: {f['reason']}" for f in failed_urls])
            detail_msg += f" Details: {reasons}"
        raise HTTPException(status_code=422, detail=detail_msg)

    # Trim oversized documents (such as giant Wikipedia pages) to avoid unneeded footer/reference clutter
    for doc in extracted_docs:
        if len(doc.page_content) > 35000:
            doc.page_content = doc.page_content[:35000]

    # Chunking: larger context chunks (1500 chars) reduce total API calls and improve context quality
    text_splitter = RecursiveCharacterTextSplitter(
        separators=['\n\n', '\n', '.', ','],
        chunk_size=1500,
        chunk_overlap=150
    )
    docs = text_splitter.split_documents(extracted_docs)
    if not docs:
        raise HTTPException(status_code=422, detail="Text splitting resulted in 0 text chunks.")

    # Safety limit to comfortably stay within Google Gemini Free Tier rate limits (100 RPM)
    if len(docs) > 40:
        docs = docs[:40]

    # Build Vector Store
    try:
        embeddings = get_embeddings()
        vectorstore = FAISS.from_documents(docs, embeddings)
        vectorstore.save_local(INDEX_DIR)
        
        # Save metadata
        successful_urls = [doc.metadata.get("source", "") for doc in extracted_docs]
        save_sources_metadata(successful_urls, len(docs))
    except Exception as e:
        err_msg = str(e)
        if "429" in err_msg or "RESOURCE_EXHAUSTED" in err_msg:
            raise HTTPException(
                status_code=429,
                detail="Google Gemini Free Tier rate limit reached (100 requests/minute). Please wait 15 seconds before indexing another article, or try with a standard news article."
            )
        raise HTTPException(status_code=500, detail=f"Failed to generate embeddings or build vector store: {err_msg}")

    return {
        "success": True,
        "message": f"Successfully indexed {len(extracted_docs)} article(s) into {len(docs)} searchable vectors.",
        "articles_indexed": len(extracted_docs),
        "total_chunks": len(docs),
        "failed_urls": failed_urls
    }

@app.post("/api/query")
def query_knowledge_base(req: QueryRequest):
    question = req.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    if not os.path.exists(os.path.join(INDEX_DIR, "index.faiss")):
        raise HTTPException(status_code=404, detail="No active index found. Please process at least one URL first.")

    try:
        embeddings = get_embeddings()
        vectorstore = FAISS.load_local(
            INDEX_DIR,
            embeddings,
            allow_dangerous_deserialization=True
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load vector store: {str(e)}")

    # Similarity search
    retrieved_docs = vectorstore.similarity_search(question, k=4)
    has_informative = any(len(d.page_content.strip()) > 100 for d in retrieved_docs) if retrieved_docs else False

    if not retrieved_docs or not has_informative:
        return {
            "answer": "The saved article(s) do not contain sufficient relevant information to answer this question. Please try asking about specific topics mentioned in the article, or index additional relevant articles.",
            "sources": [],
            "chunks_count": 0
        }

    qa_prompt_template = """Given the following extracted parts of a document and a question, create a final answer.
If you don't know the answer, just say that you don't know. Don't try to make up an answer.
Format your answer clearly with bullet points, structured headings, or key takeaways where appropriate.
ALWAYS include a "SOURCES:" section at the very end of your response listing the source names/URLs.

QUESTION: {question}
=========
{summaries}
=========
FINAL ANSWER:"""

    qa_prompt = PromptTemplate(template=qa_prompt_template, input_variables=["summaries", "question"])

    try:
        llm = get_llm()
        chain = RetrievalQAWithSourcesChain.from_chain_type(
            llm=llm,
            chain_type="stuff",
            retriever=vectorstore.as_retriever(search_kwargs={"k": 4}),
            chain_type_kwargs={"prompt": qa_prompt}
        )
        result = chain.invoke({"question": question})

        raw_answer = result.get("answer", "").strip()
        if raw_answer.startswith("FINAL ANSWER:"):
            raw_answer = raw_answer[len("FINAL ANSWER:"):].strip()

        raw_sources = result.get("sources", "")
        sources_list = []
        if raw_sources:
            for s in raw_sources.replace(",", "\n").split("\n"):
                s_clean = s.strip()
                if s_clean and s_clean not in sources_list:
                    domain = urlparse(s_clean).netloc if s_clean.startswith("http") else ""
                    sources_list.append({"url": s_clean, "domain": domain})

        # Fallback to retrieved docs metadata if chain sources is blank
        if not sources_list:
            seen = set()
            for doc in retrieved_docs:
                src = doc.metadata.get("source")
                if src and src not in seen:
                    seen.add(src)
                    domain = urlparse(src).netloc if src.startswith("http") else ""
                    sources_list.append({"url": src, "domain": domain})

        return {
            "answer": raw_answer or "No direct answer could be synthesized from the indexed articles.",
            "sources": sources_list,
            "chunks_count": len(retrieved_docs)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM synthesis error: {str(e)}")

@app.post("/api/reset")
def reset_knowledge_base():
    try:
        if os.path.exists(INDEX_DIR):
            for filename in os.listdir(INDEX_DIR):
                filepath = os.path.join(INDEX_DIR, filename)
                if os.path.isfile(filepath):
                    os.remove(filepath)
        return {"success": True, "message": "Knowledge base reset successfully."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error resetting knowledge base: {str(e)}")

# Mount Static Files and Root Route
static_dir = os.path.join(BASE_DIR, "static")
os.makedirs(static_dir, exist_ok=True)
app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.get("/")
def serve_index():
    index_file = os.path.join(static_dir, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return JSONResponse({"message": "RockyBot API running. Please ensure static/index.html is created."})

if __name__ == "__main__":
    import uvicorn
    print("\n🚀 Starting RockyBot AI Server on http://localhost:8000 ...")
    uvicorn.run("server:app", host="127.0.0.1", port=8000, reload=True)
