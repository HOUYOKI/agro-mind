# Agro-Mind

## Project Summary

Agro-Mind is an AI-powered agricultural customer support assistant. Farmers and agricultural workers submit text questions or crop images through a React chat interface; a LangGraph 12-node state machine on the backend classifies intent, checks safety risk, retrieves agronomy knowledge from a RAG knowledge base, queries product and order data, and generates a response using a locally-running Ollama LLM. High-risk or low-confidence cases are automatically escalated to a human agent queue.

## Requirements

| Requirement | Version / Notes |
|-------------|----------------|
| Python | 3.10+ |
| Node.js | 18+ |
| npm | 9+ |
| [Ollama](https://ollama.com/) | Must be running locally on `http://localhost:11434` |
| Ollama model: `qwen2.5:7b-instruct` | Used for LLM responses, intent classification, and safety checking |
| Ollama model: `bge-m3` | Used for text embedding (RAG retrieval) |
| CLIP `ViT-B/32` | Downloaded automatically by `sentence-transformers` / `open_clip` on first run |
| LangSmith account | Optional — required only if tracing is enabled via `LANGCHAIN_TRACING_V2=true` |

## Installation

**1. Pull required Ollama models** (Ollama must already be installed and running):

```bash
ollama pull qwen2.5:7b-instruct
ollama pull bge-m3
```

**2. Create and activate a Python virtual environment:**

```bash
# From the project root (agro-mind/)
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate
```

**3. Install Python dependencies:**

```bash
pip install -r requirements.txt
```

**4. Install frontend dependencies:**

```bash
cd frontend
npm install
cd ..
```

**5. Configure environment variables:**

Copy the example below into a `.env` file at the project root and fill in your values:

```
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=lsv2_pt_XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX_XXXXXXXXXXXXXXXX
LANGCHAIN_PROJECT=Agro-Mind
```

Set `LANGCHAIN_TRACING_V2=false` to disable LangSmith tracing entirely (the API key is then unused).

## Run the Project

Open **two separate terminals** from the project root.

**Terminal 1 — Backend:**

```bash
# Windows (activate venv first)
.venv\Scripts\activate
uvicorn backend.main:app --reload
```

Backend runs at `http://127.0.0.1:8000`  
API docs: `http://127.0.0.1:8000/docs`

**Terminal 2 — Frontend:**

```bash
cd frontend
npm run dev
```

Frontend runs at `http://localhost:5173`

> **Image upload via `/chat`:** The `/chat` endpoint accepts both JSON (`{"customer_id": "...", "message": "..."}`) and multipart FormData (`customer_id`, `message`, optional `image` file). When an image is included, the agent runs vision diagnosis as part of the normal graph flow. The standalone `/diagnose` endpoint also exists for direct image-only testing.

## Project Structure

```
agro-mind/
├── backend/
│   ├── main.py                   # FastAPI app, all HTTP endpoints
│   ├── agent_graph.py            # LangGraph state machine (12 nodes)
│   ├── config.yaml               # LLM, embedding, RAG, and path config
│   ├── data/
│   │   ├── products.csv                        # Product catalogue
│   │   ├── orders.jsonl                        # Order records
│   │   ├── escalations.jsonl                   # Escalation log
│   │   ├── customers.jsonl                     # Customer profile store
│   │   ├── cat1_usage_product_real.jsonl       # Raw Q&A training data (usage/product)
│   │   ├── cat2_diagnosis_real.jsonl           # Raw Q&A training data (crop diagnosis)
│   │   ├── cat3_aftersales_logistics_real.jsonl # Raw Q&A training data (logistics)
│   │   ├── cat4_safety_sensitive_real.jsonl    # Raw Q&A training data (safety)
│   │   ├── annotated_images/                   # Crop images for vision system training
│   │   └── cleaned/                            # Pre-processed versions of the catN JSONL files
│   ├── database/
│   │   ├── db.py                 # SQLAlchemy session setup
│   │   ├── models.py             # ORM models
│   │   └── agro_mind.db          # SQLite DB (auto-created on startup)
│   ├── tools/                    # Agent node implementations
│   │   ├── intent_classifier.py
│   │   ├── safety_checker.py
│   │   ├── product_recommender.py
│   │   ├── logistics_lookup.py
│   │   ├── rag_retriever.py
│   │   ├── llm_agent.py
│   │   ├── case_memory.py
│   │   ├── customer_profile.py
│   │   ├── conversation_summary.py
│   │   ├── escalation_queue.py
│   │   ├── human_escalation.py
│   │   ├── retrieve_agronomy_knowledge_local.py
│   │   └── langsmith_logger.py
│   ├── rag_v3/                   # RAG subsystem (ChromaDB + bge-m3 embeddings)
│   │   ├── src/
│   │   │   ├── retrieval_tool.py
│   │   │   ├── embeddings.py
│   │   │   └── config.py
│   │   ├── data/
│   │   │   └── clean_entities.json
│   │   ├── requirements.txt      # RAG-subsystem-specific dependencies
│   │   └── chromadb/             # ChromaDB persistence for RAG
│   ├── vision/                   # Crop image diagnosis subsystem
│   │   ├── diagnosis_tool.py
│   │   ├── config.py             # Pydantic config loader for vision system
│   │   ├── embeddings.py
│   │   ├── image_embeddings.py
│   │   ├── image_retriever.py
│   │   ├── hybrid_retriever.py
│   │   ├── retriever.py
│   │   └── ranker.py
│   ├── vision_chromadb/          # ChromaDB persistence for vision (CLIP embeddings)
│   ├── test_*.py                 # Manual integration test scripts (run from project root)
│   └── system_benchmark.py       # End-to-end benchmark runner
├── frontend/
│   ├── src/
│   │   ├── main.jsx              # React entry point
│   │   ├── App.jsx               # Main chat UI
│   │   ├── CustomerProfile.jsx   # Customer profile panel
│   │   ├── App.css
│   │   └── index.css
│   └── public/
│       ├── human_escalation.html # Escalation confirmation page
│       └── icons.svg
├── scripts/                      # Utility and testing scripts
│   ├── test_safety_checker.py
│   ├── test_ollama.py
│   └── ...
├── requirements.txt
├── .env                          # Secret environment variables (not committed)
└── .gitignore
```

## API Keys & Environment Variables

| Variable | Purpose | Where to Get It | Format |
|----------|---------|-----------------|--------|
| `LANGCHAIN_TRACING_V2` | Enable/disable LangSmith tracing | Set to `true` or `false` | `true` |
| `LANGCHAIN_API_KEY` | Authenticates with LangSmith for trace logging | [smith.langchain.com](https://smith.langchain.com) → Settings → API Keys | `lsv2_pt_XXXX...` |
| `LANGCHAIN_PROJECT` | LangSmith project name for grouping traces | Choose any name | `Agro-Mind` |

Tracing is optional. Set `LANGCHAIN_TRACING_V2=false` to run without a LangSmith account.

**There are no other required external API keys.** The LLM (`qwen2.5:7b-instruct`) and embeddings (`bge-m3`) run entirely through local Ollama.

## Known Issues

- **`backend/test_image.py` is non-functional** — it hardcodes a path to `D:\agro-mind\...` on another developer's machine. Replace with a local image path before running.

- **`backend/vision/chromadb`** — a stray 0-byte file exists at this path. It is not a directory. The actual ChromaDB data for the vision subsystem is correctly stored in `backend/vision_chromadb/`. The file has no runtime effect but should be deleted when safe.

- **`frontend/public/frontend/public/human_escalation.html`** — the escalation confirmation HTML was committed at a doubly-nested wrong path. The correct copy is now at `frontend/public/human_escalation.html`. The old path is a redundant copy and can be removed.

- **`agenticdiagram/` directory does not exist** — architecture diagram YAML files referenced in development notes have not been committed to this branch.

- **`backend/rag_v3/__init__.py` and `backend/rag_v3/src/__init__.py`** — both are 0-byte files. They are valid Python package markers and require no content, but are noted here for completeness.

- **`backend/database/agro_mind.db` is committed** — the `.gitignore` instructs it to be excluded but the file is present in the repository. This is a local SQLite database that is auto-created on backend startup; it should not be in version control.

- **Customer ID is not authenticated** — the `customer_id` field in the chat UI is a free-text input for demo/testing only. In production, this must come from a real authentication system (JWT, session, etc.).

- **All LLM inference runs locally via Ollama** — the system will not function without Ollama running and both models (`qwen2.5:7b-instruct`, `bge-m3`) pulled. There is no cloud LLM fallback.

- **Safety timeout** — the Tier 4 safety checker has a 90-second Ollama timeout. Cold model loads on first request may cause this to trigger.
