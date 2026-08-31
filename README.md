# MedAdvisor — Doctor's Personal RAG Advisor

**MedAdvisor** is a grounded Retrieval-Augmented Generation (RAG) platform designed specifically for healthcare professionals and medical researchers. It allows doctors to upload medical documents (PDFs, Word documents, text files) and ask clinical or diagnostic questions. The system returns precise, step-by-step grounded reasoning backed strictly by inline citations from the uploaded documents — with **zero hallucination or external assumptions**.

---

## 🌟 Key Features

- 📄 **Multi-Format Document Ingestion**: Supports `.pdf`, `.docx`, and `.txt` files with automated parsing, semantic text chunking, and metadata tracking.
- 🔍 **Hybrid Retrieval Engine**: Combines **Semantic Vector Search** (`sentence-transformers/all-MiniLM-L6-v2` stored in ChromaDB) and **BM25 Keyword Search** merged using **Reciprocal Rank Fusion (RRF)** for optimal retrieval accuracy.
- 🧠 **Grounded Chain-of-Thought Reasoning**: Powered by Google's latest `google-genai` SDK (`gemini-2.0-flash`), enforcing strict clinical non-hallucination rules and inline chunk citations (`[Source: filename — chunk N]`).
- 🎨 **Modern Dark-Mode UI**: Built with responsive layout, glassmorphism aesthetics, ambient background glows, and visual document library management.
- ⚡ **RESTful API**: Fast and clean API built using FastAPI.

---

## 🏗️ Architecture Overview

```
 ┌────────────────┐       ┌─────────────────┐       ┌────────────────────┐
 │                │       │  FastAPI Server │       │  Hybrid Retrieval  │
 │  Web Frontend  │ ────> │  (app/main.py)  │ ────> │  Engine (RRF)      │
 │ (HTML/CSS/JS)  │       └─────────────────┘       └─────────┬──────────┘
 └────────────────┘                                           │
                                         ┌────────────────────┴────────────────────┐
                                         ▼                                         ▼
                             ┌───────────────────────┐                 ┌───────────────────────┐
                             │  ChromaDB Vector Store│                 │  BM25 Keyword Search  │
                             │ (Semantic Embeddings) │                 │   (Lexical Matching)  │
                             └───────────┬───────────┘                 └───────────┬───────────┘
                                         │                                         │
                                         └────────────────────┬────────────────────┘
                                                              ▼
                                                   ┌──────────────────────┐
                                                   │  Google Gemini 2.0   │
                                                   │ (Grounded Reasoning) │
                                                   └──────────────────────┘
```

---

## 📁 Project Structure

```
Med-RAG/
├── app/
│   ├── config.py              # Configuration & environment settings
│   ├── main.py                # FastAPI entrypoint & static route handler
│   ├── routers/
│   │   └── api.py             # API endpoints (/upload, /query, /documents)
│   └── services/
│       ├── document_store.py  # Local JSON metadata manager
│       ├── ingestion.py       # Document parser, splitter & ChromaDB ingester
│       ├── reasoning.py       # Gemini grounded reasoning engine
│       └── retrieval.py       # Hybrid BM25 + Semantic search with RRF
├── frontend/
│   ├── index.html             # Clean modern web interface
│   ├── style.css              # Custom dark-theme design system
│   └── app.js                 # Interactive chat & document manager
├── uploads/                   # Local storage for uploaded documents
├── chroma_db/                 # Persistent vector store database
├── pyproject.toml             # Project metadata & Python configuration
├── requirements.txt           # Python dependencies
└── README.md                  # Project documentation
```

---

## 🚀 Getting Started

### Prerequisites

- **Python 3.10+** installed
- A **Google Gemini API Key** (Get one from [Google AI Studio](https://aistudio.google.com/))

### Installation & Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/Avinash-Tewari/Med-RAG.git
   cd Med-RAG
   ```

2. **Create and activate a virtual environment**
   ```bash
   # Windows (PowerShell)
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1

   # Linux / macOS
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**
   Create a `.env` file in the root directory:
   ```env
   GEMINI_API_KEY=your_gemini_api_key_here
   GEMINI_MODEL=gemini-2.0-flash
   TEMPERATURE=0.1
   ```

---

## 💻 Running the Application

Start the FastAPI development server with Uvicorn:

```bash
uvicorn app.main:app --reload
```

Open your browser and navigate to:
👉 **`http://127.0.0.1:8000`**

---

## 📡 API Endpoints

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/` | Web application home page |
| `POST` | `/api/upload` | Upload a PDF, DOCX, or TXT file for ingestion |
| `POST` | `/api/query` | Submit a clinical query to receive grounded reasoning & citations |
| `GET` | `/api/documents` | List all ingested documents |
| `DELETE` | `/api/documents/{doc_id}` | Remove a document and its vector embeddings |

---

## 🛡️ License

Distributed under the MIT License. See `LICENSE` for details.
