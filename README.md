# Project Atlas: Agentic Knowledge Compiler

> **"LLMs are more valuable as knowledge compilers than knowledge retrievers."** — Andrej Karpathy

Project Atlas (Agentic Thinking, Linking, and Synthesis) is an advanced knowledge compilation system. It treats LLMs like `gcc`, transforming a "source" directory of raw documents into a structured, highly interlinked, and human-readable markdown wiki. By pre-compiling knowledge into a high-signal substrate, Atlas eliminates the noise of flat RAG and enables more efficient agentic reasoning.

---

## 🏗️ Architecture Overview

Atlas is built as a modular Python CLI that orchestrates a hierarchy of specialized agents.

### Directory Structure (Canonical)
```bash
atlas/
├── raw/             # Source documents (human-curated intake)
│   ├── papers/      # Academic PDFs/Markdown
│   ├── articles/    # Web clips
│   └── repos/       # Codebase snapshots
├── wiki/            # Compiled knowledge (LLM-generated)
│   ├── domains/     # Concept-level articles
│   ├── connections/ # Cross-domain synthesis
│   └── _archived/   # Low-score/stale information
├── output/          # Query results, reports, and slides
├── .atlas/          # System metadata, AKL scores, and cache
└── atlas.db         # SQLite database (Hybrid Search Engine)
```

### The AI Team
- **Compiler Agent**: Processes new `raw/` files and synthesizes them into `wiki/` articles.
- **QA Agent (`lint`)**: Validates wikilink integrity and conceptual consistency.
- **Maintenance Agent (`archive`)**: Manages the **Adaptive Knowledge Lifecycle (AKL)**.
- **Synthesis Agent (`search`)**: Orchestrates multi-step reasoning across the compiled wiki.

---

## 🔄 Data Flow: The Six-Stage Pipeline

Atlas operates on a continuous feedback loop to ensure knowledge compounds over time:

1.  **INGEST**: Raw documents are fetched (via Jina Reader or pymupdf4llm) and normalized into markdown in `raw/`.
2.  **DIFF**: The system identifies new or modified sources by comparing SHA-256 hashes against the `.atlas/manifest.json`.
3.  **COMPILE**: The LLM extracts Concepts, Relationships, and Claims, then merges them into existing wiki articles or creates new ones using `[[wikilinks]]`.
4.  **INDEX**: The compiled wiki is indexed into a hybrid SQLite database combining **FTS5 BM25** and **Vector KNN** search.
5.  **QUERY**: Users or agents query the wiki. The system uses **Reciprocal Rank Fusion (RRF)** to deliver high-precision results.
6.  **LINT/ARCHIVE**: The QA agent checks for broken links, while the Maintenance agent archives stale data based on its **AKL Score** (`Importance × e^(-days/30)`).

---

## 🚀 Getting Started

### Installation
Ensure you have [uv](https://github.com/astral-sh/uv) installed:
```bash
git clone https://github.com/AV-CSE31/atlas
cd atlas
uv sync
```

### Basic Workflow
```bash
# Initialize the KB structure
uv run atlas init

# Ingest a research paper or URL
uv run atlas ingest https://arxiv.org/pdf/2404.16130

# Compile the wiki (Requires GEMINI_API_KEY)
uv run atlas compile

# Re-index and search
uv run atlas index
uv run atlas search "community summarization"

# Check knowledge graph health
uv run atlas lint
```

### Development & Testing
```bash
# Install dev dependencies
uv sync --dev

# Run the test suite
uv run pytest tests/ -v

# Run with coverage
uv run pytest tests/ --cov=src/atlas --cov-report=term-missing
```

---

## 🛠️ Key Primitives

### Adaptive Knowledge Lifecycle (AKL)
Atlas doesn't let information rot. Every article has a score:
- **Importance**: Set during compilation (0-100).
- **Recency**: Decays exponentially over a 30-day half-life.
- **Maturity**: Signals if an article is a `draft`, `validated`, or `core` knowledge.
Articles below a threshold (default 35) are moved to `_archived/` to keep the active context window lean.

### Model Context Protocol (MCP)
Atlas ships with a built-in MCP server. You can connect your compiled wiki directly to **Claude Desktop**, **Cursor**, or **VS Code**:
```bash
uv run atlas serve
```

---

## 🎯 Next Steps & Roadmap

### Tier 2: Agentic Orchestration (Current Focus)
- [ ] **Proactive Heartbeat**: Scheduled background research and gap analysis.
- [ ] **Recursive Abstractive Processing (RAPTOR)**: Hierarchical tree summarization for massive corpora.
- [ ] **Multi-Model Cascades**: Using smaller models for extraction and larger models for synthesis to optimize cost.

### Tier 3: Enterprise Graph Layer (Future)
- [ ] **GraphRAG Integration**: Community-based summarization for global sensemaking.
- [ ] **Web UI**: A Next.js dashboard for visualizing the knowledge graph.
- [ ] **Collaborative Compilation**: Multi-user support with conflict resolution.

---

## 📄 License
MIT © Ashish
