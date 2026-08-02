# 100 Days of AI — Master Syllabus

The coherence backbone. Every day's authoring reads from this first (see
`AUTHORING_TEMPLATE.md`). A day may only assume concepts from **earlier** days.
Default LLM throughout is a **free local model** (Ollama + open-source, e.g.
Llama), called behind a swappable wrapper so the provider can change without
rewriting lessons — **no paid API required** (zero-cost constraint). The
systematic-engineering thread — tests, schemas, logging, git, error handling —
is reinforced a little more each section, never front-loaded.

**Authoring status:** Days 1–80 authored (lessons + exercises + project, gate-green). Warmup + Sections 1–5 complete. Section 6 (AI Agents, Days 79–88) in progress: Day 79 (What Is an Agent? — SimpleAgent: agent loop, tool registry, safe_calculate via ast, parse_action never-raises, llm_fn injection, max_iterations) and Day 80 (The Agent Loop / ReAct — react_agent.py: Thought/Action/Observation, scratchpad, parse_react_step, trace) complete. Days 81–100 pending (next: Day 81 — Tool-Using Agents — tool_agent.py).
Update this line as days are completed.

**Day 3 prereq:** Ollama must be installed and running before starting Day 3.
- Install: macOS → `brew install ollama` (or download from ollama.com) · Linux → `curl -fsSL https://ollama.com/install.sh | sh` · Windows → installer at ollama.com
- Pull the model: `ollama pull llama3.2`
- Start the server: macOS → open the Ollama app (menu bar) · Linux/Windows → `ollama serve` in a terminal
- Install packages: `pip install ollama openai requests`

---

## Warmup — Days 1–5 · Python + First AI

| Day | Title | Objective | Key concepts | Deliverable |
|-----|-------|-----------|--------------|-------------|
| 1 | The AI Pipeline & Text-to-Speech | See a full AI system end-to-end on day one | pipelines, Edge TTS, subprocess, FFmpeg, black-box models | Personal AI Briefing Generator (headlines → spoken MP3) |
| 2 | Python for AI Engineering | Refresh the exact Python you'll use daily | functions, typing, f-strings, comprehensions, files, JSON | Data-cleaning utility script |
| 3 | Your First LLM API Call | Call an open-source model from code — three ways | Ollama (prereq: `ollama pull llama3.2`), `ollama` Python package, OpenAI-compat endpoint, raw REST via `requests`, system prompts, roles, multi-turn history | CLI Q&A assistant (free + local) |
| 4 | Structured Output & Schemas | Get reliable, typed data out of an LLM | JSON output, Pydantic schemas, validation, retries | Text → structured JSON extractor |
| 5 | Engineering Hygiene | Stop vibecoding: make code you can trust | logging, error handling, pytest, git basics | Harden Day 3's app with tests + logging |

## Section 1 — Text AI · Days 6–20

| Day | Title | Objective | Key concepts | Deliverable |
|-----|-------|-----------|--------------|-------------|
| 6 | Prompt Engineering Fundamentals | Write prompts that work reliably | anatomy of a prompt, system prompts, few-shot, roles | Prompt library that transforms text 5 ways |
| 7 | Summarization at Scale | Summarize documents longer than the context | chunking, map-reduce summarization | Long-document summarizer CLI |
| 8 | Text Classification | Categorize text with an LLM | zero-shot classification, labels, confidence | Support-ticket classifier |
| 9 | Structured Extraction | Pull entities and fields from prose | schema-guided extraction, validation | Resume → structured JSON parser |
| 10 | Prompt Templates & Reuse | Make prompts parameterized and maintainable | templating, prompt versioning | Templated prompt engine |
| 11 | Embeddings & Semantic Search | Search by meaning, not keywords | embeddings, cosine similarity, vectors | Semantic search over your notes |
| 12 | Vector Databases | Store and query vectors at scale | Chroma/FAISS, indexing, metadata | Searchable knowledge base |
| 13 | RAG I — Retrieval-Augmented Generation | Answer questions from your own data | retrieve + augment, grounding | Q&A over your documents |
| 14 | RAG II — Quality & Citations | Reduce hallucination, cite sources | chunk strategies, citations, eval | RAG with source citations |
| 15 | Building a Chatbot | Hold a multi-turn conversation | message history, conversation state | Multi-turn CLI chatbot |
| 16 | Streaming Responses | Stream tokens for good UX | streaming API, incremental output | Streaming chat |
| 17 | Tool Use / Function Calling | Let the model call your functions | tool definitions, tool loop, results | Assistant that calls calculator + weather tools |
| 18 | Cost & Token Control | Run LLMs affordably | token counting, prompt caching, cost estimation | Cost-aware API wrapper + token dashboard |
| 19 | Evaluating LLM Outputs | Measure quality objectively | LLM-as-judge, test sets, metrics | Eval harness for one of your apps |
| 20 | Capstone: Second Brain | Combine all text-AI skills | RAG + chat + citations + tests | RAG chatbot over your personal knowledge base |

## Section 2 — Automation with AI · Days 21–35

| Day | Title | Objective | Key concepts | Deliverable |
|-----|-------|-----------|--------------|-------------|
| 21 | Files at Scale | Process many files programmatically | pathlib, os, CSV/JSON, batch ops | AI file organizer/categorizer |
| 22 | Working with APIs | Consume third-party APIs well | requests, auth, pagination, rate limits | Client for a public API |
| 23 | Web Scraping Fundamentals | Extract data from web pages | BeautifulSoup, selectors, robots/ethics | Article scraper |
| 24 | AI-Powered Scraping | Turn messy pages into clean data | scrape + LLM extraction | Web page → structured JSON |
| 25 | Email Automation | Read and send email from code | SMTP/IMAP, AI drafting | AI email-responder drafter |
| 26 | Document Automation | Generate and read documents | PDF/docx read + generate | Auto-generated report from data |
| 27 | Scheduling & Cron | Run tasks automatically | APScheduler, cron, idempotency | Scheduled daily AI briefing (extends Day 1) |
| 28 | Spreadsheets & Sheets API | Read/write spreadsheets | Google Sheets API, gspread | AI that updates a tracking sheet |
| 29 | Chat Bots (Slack/Discord) | Push AI into team chat | webhooks, bot tokens, events | Notification bot with AI summaries |
| 30 | Workflow Orchestration | Chain steps reliably | pipelines, retries, state | Multi-step automation pipeline |
| 31 | Resilience & Error Handling | Survive failures gracefully | retries, backoff, dead-letter, logging | Hardened version of an earlier automation |
| 32 | Environments & Secrets | Handle keys and config safely | .env, config, secret hygiene | Secure config module |
| 33 | Batch Processing | Process thousands of items efficiently | batch API, async/concurrency | Bulk-process 1000 items |
| 34 | Building a CLI Tool | Package automation for reuse | argparse/click, entry points | Installable CLI |
| 35 | Capstone: Auto-Analyst | Ship an end-to-end automation | scrape + extract + summarize + deliver | Scheduled daily AI digest pipeline |

## Section 3 — Data & Analysis · Days 36–50

| Day | Title | Objective | Key concepts | Deliverable |
|-----|-------|-----------|--------------|-------------|
| 36 | Pandas Fundamentals | Manipulate tabular data | DataFrames, indexing, IO | Analyze a real dataset |
| 37 | Data Cleaning | Fix messy real-world data | missing values, types, dedup | Clean a messy dataset |
| 38 | Exploratory Data Analysis | Find insights in data | groupby, aggregation, pivots | EDA report |
| 39 | Data Visualization | Communicate with charts | matplotlib/plotly | Chart dashboard |
| 40 | AI-Assisted Analysis | Let an LLM narrate the data | data → narrative insights | Auto-generated data story |
| 41 | Natural Language → Pandas | Ask questions of a CSV | code generation, safe exec | Chat with your CSV |
| 42 | SQL Fundamentals | Query relational data | SQLite, SELECT, joins | Query a database |
| 43 | Natural Language → SQL | Query databases in English | text-to-SQL, guardrails | Chat with a SQL database |
| 44 | Databases in Python | Persist app data | SQLAlchemy, ORM basics | Data-backed app |
| 45 | Data Pipelines | Move and transform data | ETL, staging, transforms | ETL pipeline |
| 46 | Time Series Basics | Work with dates and trends | resampling, rolling windows | Trend analysis over time |
| 47 | Statistics for AI Engineers | Reason about data quantitatively | distributions, correlation, significance | Stats report |
| 48 | Feature Engineering & Intro ML | Train your first model | scikit-learn, train/test split | Predictive model |
| 49 | Model Evaluation | Know if a model is any good | metrics, overfitting, cross-validation | Evaluate & improve the model |
| 50 | Capstone: Insight Engine | Automate the whole analysis loop | clean + analyze + visualize + summarize | Upload data → AI executive summary |

## Section 4 — Building Real Apps · Days 51–65

| Day | Title | Objective | Key concepts | Deliverable |
|-----|-------|-----------|--------------|-------------|
| 51 | Web Apps with Streamlit | Build a UI in pure Python | widgets, state, layout | Interactive AI app UI |
| 52 | FastAPI Fundamentals | Serve AI over HTTP | REST, endpoints, request/response | AI API endpoint |
| 53 | Frontend ↔ Backend | Wire UI to API | HTTP calls, CORS, JSON contracts | Full-stack AI app |
| 54 | Databases for Apps | Save users' data | persistence, migrations | App with saved state |
| 55 | Authentication | Add users and login | sessions, hashing, API keys | App with auth |
| 56 | File Uploads & Storage | Handle user files | uploads, storage, validation | Doc-upload AI app |
| 57 | Deploying Apps | Put it on the internet | Render/Railway, env vars, HTTPS | Live deployed app |
| 58 | Streaming in Web Apps | Real-time chat UX | SSE/websockets | Deployed streaming chatbot |
| 59 | Background Jobs & Queues | Handle long tasks | workers, queues, async | App with async processing |
| 60 | Caching & Performance | Make it fast and cheap | response caching, memoization | Optimized app |
| 61 | Monitoring & Logging | See what production does | observability, error tracking | Instrumented app |
| 62 | Testing Web Apps | Ship with confidence | pytest, API tests, fixtures | Test suite for your app |
| 63 | Payments & Productization | Charge for your app | Stripe (test mode), feature gating | App with a paywall |
| 64 | Capstone Build I | Start a real product | MVP scoping, architecture | Product MVP scaffold |
| 65 | Capstone Build II | Ship the MVP | deploy + test + polish | Deployed, monetizable AI app |

## Section 5 — Vision & Multimodal · Days 66–78

| Day | Title | Objective | Key concepts | Deliverable |
|-----|-------|-----------|--------------|-------------|
| 66 | Images in Python | Manipulate images in code | PIL/Pillow, formats, resizing | Image-processing utility |
| 67 | Claude Vision | Analyze images with an LLM | multimodal messages, image input | Image describer/analyzer |
| 68 | OCR & Document AI | Extract text from images/PDFs | OCR, layout, document parsing | Receipt/invoice reader |
| 69 | Multimodal Extraction | Structured data from images | schema-guided vision extraction | Photo → structured JSON |
| 70 | Image Generation | Create images from prompts | image-gen API, prompt design | AI image generator app |
| 71 | Vision + RAG | Search images by content | image embeddings, visual search | Visual search engine |
| 72 | Speech-to-Text | Transcribe audio | Whisper, transcription, diarization | Audio transcriber |
| 73 | Text-to-Speech Deep Dive | Master voice generation | voices, SSML, rate/pitch (extends Day 1) | Podcast generator |
| 74 | Video Basics | Process video in code | frames, FFmpeg from Python | Video processor |
| 75 | Talking-Head Pipeline | Build the course's own video pipeline | Wav2Lip, lip-sync, compositing | Rebuild the lesson-video pipeline yourself |
| 76 | Multimodal Agents | Combine vision and text | screenshot understanding | Screenshot-understanding assistant |
| 77 | Real-Time Vision | Process a live camera feed | OpenCV, webcam, frame loops | Live vision demo |
| 78 | Capstone: Media Studio | One app across all modalities | transcribe + describe + generate | Multimodal media app |

## Section 6 — AI Agents · Days 79–88

| Day | Title | Objective | Key concepts | Deliverable |
|-----|-------|-----------|--------------|-------------|
| 79 | What Is an Agent? | Understand agent fundamentals | loop, tools, autonomy vs pipeline | Minimal agent from scratch |
| 80 | The Agent Loop | Reason, act, observe | ReAct, thought/action/observation | Reasoning agent |
| 81 | Tool-Using Agents | Give an agent many tools | tool routing, selection | Multi-tool assistant |
| 82 | Agent Memory | Let agents remember | short/long-term memory, persistence | Agent that remembers you |
| 83 | Planning & Decomposition | Break goals into steps | task planning, subgoals | Planner agent |
| 84 | Multi-Agent Systems | Agents that collaborate | roles, handoffs, orchestration | Researcher + writer duo |
| 85 | Model Context Protocol (MCP) | Connect agents to tools/data | MCP servers, tools, resources | MCP-connected agent |
| 86 | Retrieval Agents | Agentic RAG | tool-driven retrieval, iteration | Research agent over your docs |
| 87 | Guardrails & Safety | Keep agents controllable | validation, limits, human-in-the-loop | Safe agent with approval gates |
| 88 | Capstone: Ops Agent | Automate a real multi-step task | end-to-end autonomy + guardrails | Autonomous ops agent |

## Section 7 — Finance, Trading & Productizing · Days 89–100

| Day | Title | Objective | Key concepts | Deliverable |
|-----|-------|-----------|--------------|-------------|
| 89 | Financial Data | Get market data | market data APIs, OHLCV, storage | Fetch & store market data |
| 90 | Analyzing Markets | Compute indicators | moving averages, RSI, pandas on prices | Technical-indicator calculator |
| 91 | Backtesting Fundamentals | Test a strategy on history | simulation, look-ahead bias | Backtester |
| 92 | Building a Strategy | Turn rules into signals | entry/exit rules, signals | Strategy with buy/sell signals |
| 93 | AI-Driven Signals | Use AI for market insight | news/sentiment analysis with LLM | News-sentiment signal |
| 94 | Risk Management | Don't blow up the account | position sizing, stop-loss, drawdown | Risk-management module |
| 95 | The Trading Bot I | Architect a paper-trading bot | bot architecture, paper trading | Paper-trading bot skeleton |
| 96 | The Trading Bot II | Run it live-ish and safely | scheduling, logging, alerts | Running paper-trading bot |
| 97 | Productizing Your AI | Package a project as a product | packaging, docs, pricing | One project shipped as a product |
| 98 | Launching | Get your first users | landing page, waitlist, AI marketing | Product landing page |
| 99 | Portfolio & Personal Brand | Show the world your 100 days | portfolio, case studies | Portfolio site of your builds |
| 100 | Final Capstone | Ship your own AI product | your choice, full stack, deployed | A complete, deployed, documented AI product |
