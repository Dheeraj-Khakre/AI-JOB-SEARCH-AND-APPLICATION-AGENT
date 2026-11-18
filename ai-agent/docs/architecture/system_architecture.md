# System Architecture: Universal Local-First AI Job Search and Application Agent

## 1. Architectural Philosophy

The **Universal Local-First AI Job Search and Application Agent** is designed as a secure, local-first, highly extensible autonomous system. The architecture guarantees:

1. **Zero-Data-Leakage Local Processing**: Sensitive candidate data, resumes, portal credentials, and browsing sessions are stored and processed strictly on the user's host machine.
2. **Decoupled 5-Tier Architecture**: Clear separation of concerns between presentation, orchestration, multi-agent intelligence, local AI/vector stores, and storage/automation engines.
3. **Plug-and-Play Extensibility**: Career portal connectors, LLM providers, and document generators can be added, updated, or swapped without changing core business logic.
4. **Resilient Failure Modes**: Network dropouts, anti-bot challenges, or unavailable LLM models are handled gracefully through fallbacks, offline queues, and interactive assisted modes.

---

## 2. Five-Tier System Topology

```mermaid
flowchart TD
    subgraph TIER1 ["Tier 1: Presentation Layer"]
        UI["React 18 + TypeScript + Vite + Tailwind CSS<br/>15 Specialized Modular Pages & Dashboards<br/>Zustand Reactive State + WebSockets Client"]
    end

    subgraph TIER2 ["Tier 2: API & Gateway Layer"]
        FastAPI["FastAPI 0.111+ Async REST Gateway (127.0.0.1:8000)<br/>Pydantic v2 Request/Response Validation<br/>CORS Security Middleware & Origin Verification<br/>Real-Time WebSocket Streaming Engine"]
    end

    subgraph TIER3 ["Tier 3: Multi-Agent Orchestration Layer"]
        LangGraph["LangGraph State Machine Engine<br/>Typed JobSearchState & Persistent Memory<br/>Cycle & Hallucination Prevention Nodes<br/>Human-in-the-Loop (HITL) Cryptographic Gatekeeper"]
        Agents["8 Specialized Autonomous Agents"]
    end

    subgraph TIER4 ["Tier 4: Local AI & Vector Engine Layer"]
        Ollama["Ollama Local Inference Runtime (127.0.0.1:11434)<br/>Models: Qwen2.5-7B / Llama3.2-3B / DeepSeek-R1"]
        Embeddings["Local Embedding Engine (nomic-embed-text / bge-small)"]
        Chroma["ChromaDB Local Embedded Vector Database<br/>Collections: Resume Chunks, Job Descriptions, Skills Taxonomy"]
        CloudAdapter["Optional Cloud Fallback Adapter (OpenAI / Gemini / Anthropic)<br/>*Requires Signed Explicit User Consent*"]
    end

    subgraph TIER5 ["Tier 5: Storage & Browser Automation Layer"]
        SQLStore["Dual Relational Engine (SQLite Local / PostgreSQL Prod)<br/>SQLAlchemy 2.0 Async ORM + Alembic Migrations"]
        Vault["Encrypted Secrets Vault (AES-256-GCM + Windows DPAPI)"]
        Playwright["Playwright Browser Automation Sandbox<br/>Isolated Profile Cache per Portal + Anti-Bot Heuristics"]
        Connectors["Universal Portal Connector Registry (14+ Prebuilt Connectors)"]
    end

    TIER1 <-->|HTTP/REST & WebSockets| TIER2
    TIER2 --> TIER3
    TIER3 <--> TIER4
    TIER3 <--> TIER5
    Connectors --> Playwright
```

---

## 3. Communication Protocols and Boundaries

| Boundary | Transport | Data Format | Security Controls |
| :--- | :--- | :--- | :--- |
| **Frontend $\leftrightarrow$ Backend** | HTTP/1.1 & WebSockets | JSON / Protobuf / Binary PDF | Bound to `127.0.0.1`, strict CORS origin `localhost:5173`, CSRF token headers. |
| **Backend $\leftrightarrow$ Ollama** | HTTP (REST) | JSON (Ollama API format) | Internal localhost connection only (`127.0.0.1:11434`). Timeouts & circuit breakers. |
| **Backend $\leftrightarrow$ ChromaDB** | In-Process Python SDK | Native PyArrow / NumPy | File-level permissions inside `./data/chroma`. |
| **Backend $\leftrightarrow$ Playwright** | Node/Python IPC Bridge | CDP (Chrome DevTools Protocol) | Bound to ephemeral internal IPC pipes; debugging ports never exposed externally. |
| **Playwright $\leftrightarrow$ Public Portals** | HTTPS | HTML, DOM, HTTP Headers | Standard TLS, isolated browser cookies per portal, user-agent rotation. |

---

## 4. Local vs Production Architectural Differences

| Subsystem | Local Development Mode (Default) | Production / Cloud Deployment |
| :--- | :--- | :--- |
| **Database** | SQLite via `aiosqlite` (`./data/db/app.db`) | PostgreSQL 16+ via `asyncpg` |
| **AI Inference** | Local Ollama (`http://127.0.0.1:11434`) | Dedicated vLLM/Ollama host or enterprise cloud API |
| **Vector Storage** | Local ChromaDB embedded directory | Distributed ChromaDB / pgvector / Qdrant |
| **Credentials Vault**| Local AES-256-GCM + Windows DPAPI | HashiCorp Vault or AWS KMS / Azure Key Vault |
| **Browser Execution**| Local Playwright with headful window option | Headless Playwright running in Docker sidecar container |
| **Task Queue** | Python `asyncio` background tasks | Redis + Celery / ARQ asynchronous queue |

---

## 5. Resilience & Fault Tolerance Mechanisms

1. **Ollama Availability Heartbeat**: If the local Ollama service is stopped or restarting, the backend does not crash. It transitions to `DEGRADED_LOCAL` mode, returns actionable error prompts to the UI, and pauses active agent workflows safely.
2. **Form Automation Fail-Safe**: If an unexpected DOM mutation, dynamic iframe, or CAPTCHA appears during Playwright automation, the browser pauses execution, takes an annotated screenshot, and transfers control to the user via **Level 4 Assisted Manual Mode**.
3. **Database Write Integrity**: SQLite is configured with Write-Ahead Logging (`PRAGMA journal_mode=WAL`) and `PRAGMA synchronous=NORMAL`, preventing database corruption during abrupt process terminations.
