# Charles

A personal AI assistant built on LangChain Deep Agents and LangGraph, running completely free of charge by using models served by the free OpenRouter API and LM studio.

The goal: an assistant with real memory, real tools, and real access to your own files and data, all to streamline workflows and improve productivity
as an all-in-one agent

---

## Overview

`Charles` combines three subsystems into one coherent assistant:

- **Agent core** — a Deep Agent (planning, tool use, context management) served by OpenRouter
- **Retrieval (RAG)** — a local vector store over your own documents, exposed to the agent as a tool
- **Tools & persistence** — filesystem, notes, calendar, and other tools, backed by local storage

---

## Features

### Current
- [x] Model served via OpenRouter API
- [x] Deep Agent core with planning and context management (via `deepagents`)
- [x] Local document embedding and retrieval pipeline (Chroma)
- [x] Conversational memory across sessions (LangGraph checkpointer)
- [x] Scoped filesystem access tool
- [x] Notes / todo tool with local persistence
- [x] MCP server served by Browser OS allowing full web access free of charge
### In progress / planned
- [ ] Desktop app and UI using React and Electron
- [ ] Calendar and email integration (read-only first)
- [ ] Human-in-the-loop approval for sensitive actions (sending messages, deleting files, running shell commands)
- [ ] Voice input/output

---

## Architecture

```                                                
User ──▶ UI ──▶ Agent Core (deepagents) ──▶ Tools ──▶ Local and external data
                                          │       
                                          ▼
                                   OpenRouter API
```
---

## Project Structure

```
localAgent/
├── agent/
│   ├── agent.py            # agent construction (create_deep_agent)
│   └── system_prompt.py   # system prompt as a standalone template
├── tools/
│   ├── rag.py
│   ├── todo.py
|   ├── web.py
│   └── tools.py
├── memory/
│   ├── vectorstore.py     # embedding + indexing
├── db/
│   └── db.py         # local SQLite persistence
├── interfaces/
│   ├── cli.py
├── config/
│   └── settings.py        # tool toggles, sandboxed paths, permissions
```

---

## Tech Stack

| Layer | Choice |
|---|---|
| Agent framework | LangChain `deepagents` + LangGraph |
| Model serving | OpenRouter/LM studio |
| Vector store | Chroma |
| Persistence | SQLite |
| MCP connections | Browser OS |

## Getting Started

```bash
git clone https://github.com/Rayablepy/localAgent.git
cd localAgent
pip install -r requirements.txt
cp .env.example .env   
```

Requires [LM Studio](https://lmstudio.ai/) (or another OpenAI-compatible local server) running at `http://localhost:1234/v1` with JIT loading enabled and an OpenRouter API key. 
For browser OS use, Browser OS must be installed with the MCP server running locally on port 9010(can be changed in settings.py).

```bash
python -m execution.py cli
```

---

## License

TBD
