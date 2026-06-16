# Natural Language Processing - Mountain Trail Advisor

This is an ongoing project building an intelligent, AI-powered conversational agent that recommends mountain trails in the Tatra Mountains.

The system uses a Retrieval-Augmented Generation (RAG) architecture combined with Persistent State Tracking / Slot Filling. It collects user preferences during the conversation, retrieves relevant trail candidates using semantic search and recommends the most suitable route based on structured trail metadata.

> **Note:** This project is actively being developed. New features and improvements will be added.

## Architecture

* **Backend:** Python + Flask
* **Frontend:** HTML / JavaScript / CSS
* **Vector Database:** FAISS
* **Embeddings:** `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`
* **Metadata Extraction:** LLM-assisted structured information extraction + Pydantic validation
* **Recommendation Logic:** FAISS semantic retrieval + metadata-based trail scoring
* **LLM Engine:** Local Ollama, configurable via `.env`
* **Dialogue Management:** Persistent State Tracking / Slot Filling

The project supports separate local LLM models for different tasks:

* `OLLAMA_EXTRACT_MODEL` — extracts user preferences from chat messages.
* `OLLAMA_RESPONSE_MODEL` — generates the final natural language recommendation.
* `OLLAMA_METADATA_MODEL` — extracts structured trail metadata from scraped articles.

This makes it possible to use a fast model such as `llama3.2` for frequent chat interactions, while optionally using a stronger Polish-focused model such as Bielik for metadata extraction or final answer generation.

## Setup & Installation

### 1. Install Ollama and the Language Model

This project relies on running the LLM locally on your machine. Ollama is used to serve the language model.

**Install Ollama macOS / Linux:**

```bash
curl -fsSL https://ollama.com/install.sh | sh
```

**Download the default model:**

```bash
ollama run llama3.2
```

You can type `/bye` to exit the interactive prompt once the model finishes downloading.

Optionally, you can use a Polish-focused model such as Bielik:

```bash
ollama run hf.co/speakleash/Bielik-11B-v2.3-Instruct-GGUF:Q4_K_M
```

To check installed models, run:

```bash
ollama list
```

## 2. Configure Environment Variables

Create a `.env` file in the root project directory.

Default configuration using only `llama3.2`:

```env
OLLAMA_URL=http://localhost:11434/api/chat

OLLAMA_EXTRACT_MODEL=llama3.2
OLLAMA_RESPONSE_MODEL=llama3.2
OLLAMA_METADATA_MODEL=llama3.2

EMBEDDING_MODEL=sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
```

This configuration is recommended for slower computers or for users who do not have Bielik installed.

You can also use a mixed configuration. For example, fast chat extraction with `llama3.2`, but Bielik for final answers and metadata extraction:

```env
OLLAMA_URL=http://localhost:11434/api/chat

OLLAMA_EXTRACT_MODEL=llama3.2
OLLAMA_RESPONSE_MODEL=hf.co/speakleash/Bielik-11B-v2.3-Instruct-GGUF:Q4_K_M
OLLAMA_METADATA_MODEL=hf.co/speakleash/Bielik-11B-v2.3-Instruct-GGUF:Q4_K_M

EMBEDDING_MODEL=sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
```

You can also use Bielik for every LLM task:

```env
OLLAMA_URL=http://localhost:11434/api/chat

OLLAMA_EXTRACT_MODEL=hf.co/speakleash/Bielik-11B-v2.3-Instruct-GGUF:Q4_K_M
OLLAMA_RESPONSE_MODEL=hf.co/speakleash/Bielik-11B-v2.3-Instruct-GGUF:Q4_K_M
OLLAMA_METADATA_MODEL=hf.co/speakleash/Bielik-11B-v2.3-Instruct-GGUF:Q4_K_M

EMBEDDING_MODEL=sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
```

> **Note:** Bielik may produce better Polish-language metadata and final answers, but it is slower than `llama3.2` on weaker machines.

## 3. Prepare Python Environment

It is recommended to use Python 3.11.

Example with Conda:

```bash
conda create -n nlp311 python=3.11 -y
conda activate nlp311
python -m pip install --upgrade pip setuptools wheel
python -m pip install -r requirements.txt
```

Alternative using `venv`:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

> **Note:** Python 3.11 is recommended because some dependencies, such as PyTorch and FAISS, may not work correctly with newer Python versions.

## 4. Generate Data, Extract Metadata & Build Embeddings

Before running the server, make sure you have scraped trail articles, extracted structured metadata and generated the FAISS embedding index.

Run the full pipeline from the root project directory:

```bash
python scripts/scraper.py
python scripts/extract_metadata.py
python scripts/generate_embeddings.py
```

The pipeline works as follows:

1. `scraper.py` downloads raw trail articles from supported websites and stores them as JSON files in the `data/` directory.
2. `extract_metadata.py` uses an LLM-assisted extraction step to convert raw articles into structured trail metadata.
3. `generate_embeddings.py` builds semantic embeddings from the processed metadata and saves the FAISS input files.

The metadata extraction step uses the model configured in:

```env
OLLAMA_METADATA_MODEL
```

This means you can use `llama3.2` for metadata extraction, or optionally use Bielik for better Polish-language extraction.

The processed metadata includes fields such as:

* trail name,
* region,
* duration,
* distance,
* elevation gain,
* difficulty,
* technical difficulty,
* exposure,
* suitability for beginners,
* suitability for children,
* risks,
* attractions,
* recommended season.

Processed metadata files are stored in:

```bash
data/processed/
```

The generated embedding files are saved as:

```bash
data/embeddings.npy
data/index_mapping.json
```

If the raw articles have already been downloaded, you do not need to run the scraper again. In that case, run only:

```bash
python scripts/extract_metadata.py
python scripts/generate_embeddings.py
```

If `data/processed/` already exists and you only changed the chatbot response model in `.env`, you do not need to regenerate metadata or embeddings.

You should regenerate metadata when:

* you want to re-extract trail information with a different metadata model,
* the metadata extraction prompt changes,
* raw scraped articles change,
* new trail files are added.

You should regenerate embeddings when:

* processed trail JSON files change,
* the embedding model changes,
* the dataset is scraped again,
* new processed trail files are added.

## 5. Run the Application

Start the Flask server:

```bash
python app.py
```

Then open your web browser and navigate to:

```text
http://localhost:5000
```

## State Tracking Logic

To avoid the LLM forgetting past context, the application uses Persistent State Tracking.

The user profile is stored as structured JSON and updated during the conversation. The profile includes fields such as:

* experience level,
* fitness level,
* time or distance limit,
* preferred difficulty,
* exposure tolerance,
* group type,
* children,
* trail preferences,
* health limitations.

This allows the system to maintain a stable user profile instead of relying only on the raw conversation history.

The model configured as:

```env
OLLAMA_EXTRACT_MODEL
```

is used for extracting user preferences from each chat message.

## Recommendation Logic

The recommendation process consists of several steps:

1. The user describes their preferences in natural language.
2. The LLM extracts structured information into a user profile.
3. FAISS retrieves semantically relevant trail candidates.
4. A scoring function ranks candidates using structured metadata.
5. The final LLM response explains the best recommendation in natural language.

The scoring logic takes into account:

* time limit,
* difficulty level,
* user experience,
* fitness level,
* exposure tolerance,
* elevation gain,
* suitability for beginners,
* suitability for children,
* risks,
* attractions and user preferences.

The final response is generated using the model configured as:

```env
OLLAMA_RESPONSE_MODEL
```

This hybrid approach combines semantic search, structured metadata, deterministic scoring and conversational explanation.



## Model Configuration Examples

Fast setup for all users:

```env
OLLAMA_EXTRACT_MODEL=llama3.2
OLLAMA_RESPONSE_MODEL=llama3.2
OLLAMA_METADATA_MODEL=llama3.2
```

Recommended setup for better Polish metadata extraction:

```env
OLLAMA_EXTRACT_MODEL=llama3.2
OLLAMA_RESPONSE_MODEL=llama3.2
OLLAMA_METADATA_MODEL=hf.co/speakleash/Bielik-11B-v2.3-Instruct-GGUF:Q4_K_M
```

Recommended setup for better final Polish responses:

```env
OLLAMA_EXTRACT_MODEL=llama3.2
OLLAMA_RESPONSE_MODEL=hf.co/speakleash/Bielik-11B-v2.3-Instruct-GGUF:Q4_K_M
OLLAMA_METADATA_MODEL=hf.co/speakleash/Bielik-11B-v2.3-Instruct-GGUF:Q4_K_M
```

## Project Status

This project is under active development. Planned improvements include:

* better metadata extraction,
* improved trail scoring,
* optional model comparison between `llama3.2` and Bielik,
* richer frontend controls,
* more transparent recommendation explanations,
* improved handling of contradictory user requirements.
