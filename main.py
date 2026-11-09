import os
import streamlit as st
import time
from dotenv import load_dotenv

from langchain_core.prompts import PromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
try:
    from langchain_classic.chains import RetrievalQAWithSourcesChain
except ImportError:
    from langchain.chains import RetrievalQAWithSourcesChain  # type: ignore[import-not-found]

from langchain_community.document_loaders import WebBaseLoader
from langchain_community.vectorstores import FAISS
from langchain_text_splitters import RecursiveCharacterTextSplitter

# Load environment variables from .env file
load_dotenv()

api_key = os.getenv("GOOGLE_API_KEY")

st.title("RockyBot: News Research Tool 📈")
st.sidebar.title("News Article URLs")

if not api_key:
    st.warning("⚠️ Please configure `GOOGLE_API_KEY` in your `.env` file to use RockyBot.")

if "url_count" not in st.session_state:
    st.session_state.url_count = 1

st.sidebar.caption("💡 Enter **1 or more** news article URLs below:")

col_add, col_rem = st.sidebar.columns(2)
if col_add.button("➕ Add URL"):
    st.session_state.url_count += 1
if col_rem.button("➖ Remove") and st.session_state.url_count > 1:
    st.session_state.url_count -= 1

urls = []
for i in range(st.session_state.url_count):
    label = f"Article URL {i+1}" if st.session_state.url_count > 1 else "Article URL"
    url = st.sidebar.text_input(label, key=f"url_input_{i}")
    urls.append(url)

process_url_clicked = st.sidebar.button("🚀 Process & Index URLs", use_container_width=True)
index_path = "faiss_store_gemini"

main_placeholder = st.empty()

import re
from langchain_core.embeddings import Embeddings

class ThrottledGoogleEmbeddings(Embeddings):
    """Wraps Google embeddings with batching and automatic retry on 429 rate limits."""
    def __init__(self, base_embeddings, batch_size=15, delay_between_batches=0.6, max_retries=3):
        self.base = base_embeddings
        self.batch_size = batch_size
        self.delay_between_batches = delay_between_batches
        self.max_retries = max_retries

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
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
                            time.sleep(delay)
                            continue
                    raise e
            if i + self.batch_size < total:
                time.sleep(self.delay_between_batches)
        return all_embeddings

    def embed_query(self, text: str) -> list[float]:
        for attempt in range(self.max_retries):
            try:
                return self.base.embed_query(text)
            except Exception as e:
                err_msg = str(e)
                if ("429" in err_msg or "RESOURCE_EXHAUSTED" in err_msg) and attempt < self.max_retries - 1:
                    time.sleep(16.0)
                    continue
                raise e

if api_key:
    llm = ChatGoogleGenerativeAI(
        model="gemini-flash-lite-latest",
        temperature=0.2,
        max_output_tokens=500
    )
    base_embeddings = GoogleGenerativeAIEmbeddings(
        model="gemini-embedding-2",
        output_dimensionality=1536
    )
    embeddings = ThrottledGoogleEmbeddings(base_embeddings, batch_size=15, delay_between_batches=0.6)

qa_prompt_template = """Given the following extracted parts of a document and a question, create a final answer.
If you don't know the answer, just say that you don't know. Don't try to make up an answer.
ALWAYS include a "SOURCES:" section at the very end of your response listing the source names.

QUESTION: {question}
=========
{summaries}
=========
FINAL ANSWER:"""

qa_prompt = PromptTemplate(template=qa_prompt_template, input_variables=["summaries", "question"])


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


if process_url_clicked:
    if not api_key:
        st.error("API Key is missing. Please set GOOGLE_API_KEY in your .env file.")
    else:
        valid_urls = [u.strip() for u in urls if u.strip()]

        if not valid_urls:
            st.error("Please enter at least one valid URL.")
        else:
            extracted_docs = []
            failed_urls = []

            main_placeholder.text("Data Loading...Started...✅✅✅")
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
                        failed_urls.append((url, "No content extracted (empty page)."))
                        continue

                    doc = loaded[0]
                    doc.metadata["source"] = url
                    is_valid, reason = is_informative_content(doc.page_content)
                    if not is_valid:
                        failed_urls.append((url, reason))
                    else:
                        extracted_docs.append(doc)
                except Exception as e:
                    failed_urls.append((url, f"Error fetching URL: {str(e)}"))

            if failed_urls:
                st.error("⚠️ Failed to extract content from the following URL(s):")
                for u, reason in failed_urls:
                    st.markdown(f"- **{u}**: {reason}")
                st.info(
                    "💡 Some news sites (such as Reuters or Bloomberg) enforce strict anti-bot protections or paywalls. "
                    "For best results, use publicly accessible articles from sources like CNBC, BBC, TechCrunch, Yahoo Finance, etc."
                )

            if not extracted_docs:
                st.error("No valid article content could be extracted. The FAISS index was not created or modified.")
                st.stop()

            for doc in extracted_docs:
                if len(doc.page_content) > 35000:
                    doc.page_content = doc.page_content[:35000]

            text_splitter = RecursiveCharacterTextSplitter(
                separators=['\n\n', '\n', '.', ','],
                chunk_size=1500,
                chunk_overlap=150
            )
            main_placeholder.text("Text Splitter...Started...✅✅✅")
            docs = text_splitter.split_documents(extracted_docs)

            if not docs:
                st.error("Text splitting produced 0 chunks. The FAISS index was not created or modified.")
                st.stop()

            if len(docs) > 40:
                docs = docs[:40]

            main_placeholder.text("Embedding Vector Started Building...✅✅✅")
            vectorstore_gemini = FAISS.from_documents(docs, embeddings)
            time.sleep(1)

            vectorstore_gemini.save_local(index_path)
            main_placeholder.text("FAISS Index Successfully Built & Saved! 🎉")
            st.success(f"Successfully processed {len(extracted_docs)} article(s) into {len(docs)} text chunks!")

query = main_placeholder.text_input("Question: ")
if query:
    if not api_key:
        st.error("API Key is missing. Please set GOOGLE_API_KEY in your .env file.")
    elif os.path.exists(index_path):
        vectorstore = FAISS.load_local(
            index_path,
            embeddings,
            allow_dangerous_deserialization=True
        )

        retrieved_docs = vectorstore.similarity_search(query, k=4)
        has_informative_content = any(len(d.page_content.strip()) > 100 for d in retrieved_docs) if retrieved_docs else False

        if not retrieved_docs or not has_informative_content:
            st.warning("The saved articles do not contain enough relevant information to answer this question.")
        else:
            chain = RetrievalQAWithSourcesChain.from_chain_type(
                llm=llm,
                chain_type="stuff",
                retriever=vectorstore.as_retriever(),
                chain_type_kwargs={"prompt": qa_prompt}
            )
            result = chain({"question": query}, return_only_outputs=True)

            st.header("Answer")
            answer = result.get("answer", "").strip()
            if answer.startswith("FINAL ANSWER:"):
                answer = answer[len("FINAL ANSWER:"):].strip()
            st.write(answer if answer else "No answer generated.")

            sources = result.get("sources", "")
            if sources:
                st.subheader("Sources:")
                sources_list = sources.split("\n")
                for source in sources_list:
                    source_str = source.strip()
                    if source_str:
                        if source_str.startswith("http://") or source_str.startswith("https://"):
                            st.markdown(f"- [{source_str}]({source_str})")
                        else:
                            st.markdown(f"- {source_str}")
    else:
        st.info("No saved vector index found. Please process URLs first.")
