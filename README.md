# Natural Language Processing - Mountain Trail Advisor

This is an ongoing project building an intelligent, AI-powered conversational agent that recommends mountain trails in the Tatra Mountains. It uses a Retrieval-Augmented Generation (RAG) architecture combined with Persistent State Tracking (Slot Filling) to gather user requirements systematically.

> **Note:** This project is actively being developed. New features and improvements will be added.

## Architecture

- **Backend:** Python + Flask
- **Frontend:** HTML/JS/CSS
- **Vector Database:** FAISS
- **Embeddings:** `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`
- **LLM Engine:** Local Ollama (`llama3.2`)

## Setup & Installation

### 1. Install Ollama and the Language Model

This project relies on running the LLM locally on your machine for privacy and speed. We use Ollama for this purpose.

**Install Ollama (macOS / Linux):**
```bash
curl -fsSL https://ollama.com/install.sh | sh
```

**Download the required model (`llama3.2`):**
```bash
ollama run llama3.2
```
*(You can type `/bye` to exit the interactive prompt once it finishes downloading).*

### 2. Prepare Python Environment

It is recommended to use a virtual environment:
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

*(Note: Ensure you have installed FAISS and SentenceTransformers as part of your dependencies).*

### 3. Generate Data & Embeddings

Before running the server, make sure you have scraped the data and generated the FAISS index:

```bash
# Inside the virtual environment
cd scripts
python scraper.py
python generate_embeddings.py
cd ..
```

### 4. Run the Application

Start the Flask server:
```bash
python app.py
```
Then, open your web browser and navigate to: `http://localhost:5000`

## State Tracking Logic

To avoid the LLM "forgetting" past context, the application uses a Persistent State Tracking architecture. The extracted form (JSON) is maintained dynamically by the frontend and passed into the RAG engine upon every request. The LLM only receives the most recent message, drastically reducing context window overhead and hallucination risks for Small Language Models (SLMs).
