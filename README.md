
# RockyBot AI: Next-Gen News & Financial Research Engine 📈

RockyBot AI is an enterprise-grade AI research platform designed for fast, accurate information retrieval across financial news, market reports, and domain-specific articles. Powered by **Google Gemini** (`gemini-flash-lite-latest` + `gemini-embedding-2`) and **FAISS** vector search with a custom **Modern Web Application** (FastAPI + Vanilla CSS/JS) and flexible URL ingestion.

---

## 🚀 Key Improvements & Features

* **Flexible Ingestion (Single or Multi-URL):** No longer forced to provide 3 URLs. Index **just 1 single article** or dynamically add as many as needed with a single click.
* **Modern High-Performance Web UI:** Replaced the clunky default layout with a responsive, glassmorphic dark-mode web application featuring real-time status indicators, stepper progress tracking, quick prompt chips, and verified citation cards.
* **Google Gemini 2.0 & FAISS Integration:** High-speed vector search with 1536-dimensional embeddings and low-latency synthesis.
* **Automated Anti-Bot & Content Validation:** Intelligently screens out CAPTCHAs, paywalls, and empty pages to ensure high indexing quality.
* **Verifiable Source Citations:** Every synthesized answer provides direct source links back to the original article with domain tags and one-click copy.

---

## 🛠️ Quick Start

### 1. Configure API Key
Create or verify your `.env` file in the project root:
```env
GOOGLE_API_KEY=your_gemini_api_key_here
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Launch the Modern Web Application (Recommended)
```bash
python run.py
```
This automatically starts the server and opens your browser at **`http://localhost:8000`**.

*(Alternatively, you can run `uvicorn server:app --reload` or `streamlit run main.py` for the legacy interface).*

---

## 📁 Project Structure

* **`server.py`**: FastAPI backend implementing the RAG ingestion and retrieval endpoints (`/api/process-urls`, `/api/query`, `/api/status`, `/api/reset`).
* **`static/`**:
  * `index.html`: Modern, responsive layout with Step 1 (Sources) and Step 2 (Q&A).
  * `index.css`: Custom vanilla CSS styling with sleek glassmorphism, responsive grid, and micro-animations.
  * `app.js`: Client-side logic for dynamic URL inputs, progress stepper, prompt chips, and clipboard copy.
* **`run.py`**: One-click launcher that starts the server and opens the browser.
* **`main.py`**: Updated Streamlit application (now also supports single or dynamic URLs).
* **`faiss_store_gemini/`**: Local FAISS vector index directory and metadata storage.
* **`requirements.txt`**: Package dependencies.