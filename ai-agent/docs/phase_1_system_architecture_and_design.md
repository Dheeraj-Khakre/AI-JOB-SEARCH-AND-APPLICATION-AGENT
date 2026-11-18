# Phase 1: Universal Local-First AI Job Search and Application Agent
## System Architecture, Threat Model, Multi-Agent Design & Technical Specification

This document defines the production system design, multi-agent coordination, database schema, threat model, folder structure, and execution plan for the Universal Local-First AI Job Search and Application Agent.

Refer to the primary architectural artifact and design specification:
- **System Architecture**: 5-tier decoupled model (React UI, FastAPI/LangGraph API, Multi-Agent Intelligence, Local Ollama/Chroma AI layer, Storage & Browser Automation).
- **Multi-Agent Design**: 8 specialized LangGraph agents with Human-in-the-Loop approval gate.
- **Portal Connectors**: 4-level plugin architecture with support for Level 1 (API), Level 2 (ATS: Greenhouse, Lever, Workday, etc.), Level 3 (Generic Browser Heuristic), and Level 4 (Assisted Manual).
- **Database Schema**: 17 SQLAlchemy/Alembic tables supporting both SQLite and PostgreSQL.
- **Security & Privacy**: STRIDE-evaluated threat model with strict anti-hallucination verification, AES-256-GCM vault, prompt-injection defense, and local zero-data-leakage default.
- **Folder Structure**: Clean enterprise monorepo layout (`backend/`, `frontend/`, `data/`, `scripts/`, `docker/`, `docs/`).
- **Execution Architecture**: Windows 10/11 batch automation (`start_backend.bat`, `start_frontend.bat`, `start_all.bat`, `stop_all.bat`).
- **Implementation Roadmap**: 13-phase sequential engineering plan.
