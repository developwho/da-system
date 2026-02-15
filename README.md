<p align="center">
  <img src="frontend/da-insights-hub/public/icon.svg" width="80" alt="DA System Logo" />
</p>

<h1 align="center">DA System</h1>

<p align="center">
  <strong>AI-Powered Data Analysis Automation Agent</strong><br/>
  Upload your data. Get a full analysis report. No expertise required.
</p>

<p align="center">
  <a href="#quick-start">Quick Start</a> &middot;
  <a href="#features">Features</a> &middot;
  <a href="#architecture">Architecture</a> &middot;
  <a href="#tech-stack">Tech Stack</a> &middot;
  <a href="#api-reference">API Reference</a> &middot;
  <a href="#license">License</a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/python-3.11+-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python" />
  <img src="https://img.shields.io/badge/react-18-61DAFB?style=flat-square&logo=react&logoColor=black" alt="React" />
  <img src="https://img.shields.io/badge/fastapi-0.109-009688?style=flat-square&logo=fastapi&logoColor=white" alt="FastAPI" />
  <img src="https://img.shields.io/badge/license-MIT-green?style=flat-square" alt="License" />
</p>

---

## What is DA System?

DA System is an **end-to-end data analysis automation platform** that transforms raw CSV/Excel files into professional-grade analysis reports through an AI agent pipeline.

The system handles the entire workflow autonomously:

```
Data Upload → Problem Definition → Literature Review → AutoML Modeling → SHAP Insights → Report
```

A conversational AI interface guides non-technical users through the process, asking intelligent questions about the data before running analysis. The full pipeline completes in **15-30 minutes** with no manual intervention.

---

## Features

### Agent Pipeline
- **Problem Definition Agent** &mdash; Conversational Q&A to understand your data and define analysis goals with adaptive metrics
- **Research Coordinator** &mdash; Parallel literature review across HuggingFace Papers, Kaggle Solutions, and Gemini Deep Research
- **Modeling Agent** &mdash; FLAML AutoML with smart preprocessing (outlier clipping, encoding, imbalance handling)
- **Insight Agent** &mdash; SHAP-based feature importance, Cohen's d effect sizes, confusion matrix analysis
- **Reporting Agent** &mdash; McKinsey-quality HTML reports with KPI cards, CSS bar charts, and print-ready A4 layout

### Platform
- **Real-time Progress** &mdash; WebSocket-powered live updates with phase-based substep tracking
- **Interactive Q&A** &mdash; AI asks domain-specific questions before analysis (outlier handling, class imbalance warnings)
- **Data Intelligence** &mdash; Automatic domain detection (10 domains), target variable scoring, imbalance/outlier detection
- **MLflow Tracking** &mdash; Full experiment tracking with model artifacts and feature importance
- **Dark Mode** &mdash; Complete dark/light theme support

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    React Frontend                       │
│              (Vite + Tailwind + shadcn/ui)              │
└──────────┬──────────────────────┬───────────────────────┘
           │ REST API             │ WebSocket
           ▼                      ▼
┌─────────────────────────────────────────────────────────┐
│                   FastAPI Backend                       │
│                                                         │
│  ┌─────────────────────────────────────────────────┐    │
│  │            Orchestrator Agent                    │    │
│  │                                                  │    │
│  │  ┌──────────────┐    ┌───────────────────────┐  │    │
│  │  │   Problem     │    │  Research Coordinator │  │    │
│  │  │  Definition   │    │  ├─ HuggingFace       │  │    │
│  │  └──────┬────────┘    │  ├─ Kaggle            │  │    │
│  │         │              │  └─ Deep Research     │  │    │
│  │         ▼              └──────────┬────────────┘  │    │
│  │  ┌──────────────┐               │               │    │
│  │  │   Modeling    │◄──────────────┘               │    │
│  │  │  (FLAML)      │                               │    │
│  │  └──────┬────────┘                               │    │
│  │         ▼                                         │    │
│  │  ┌──────────────┐    ┌──────────────┐            │    │
│  │  │   Insight     │───▶│  Reporting   │            │    │
│  │  │  (SHAP+LLM)  │    │  (HTML+MD)   │            │    │
│  │  └──────────────┘    └──────────────┘            │    │
│  └─────────────────────────────────────────────────┘    │
│                                                         │
└─────┬──────────────┬──────────────┬─────────────────────┘
      │              │              │
   Redis          MLflow       File Storage
  (Sessions)    (Tracking)     (Uploads)
```

---

## Tech Stack

| Layer | Technologies |
|-------|-------------|
| **Frontend** | React 18, Vite, TypeScript, Tailwind CSS, shadcn/ui, React Query |
| **Backend** | FastAPI, Redis, Celery, WebSocket |
| **ML/AutoML** | FLAML, XGBoost, LightGBM, CatBoost, scikit-learn |
| **Explainability** | SHAP |
| **Experiment Tracking** | MLflow |
| **LLM** | Gemini Flash 3.0 (primary), OpenAI, Anthropic (fallback) |
| **External Data** | HuggingFace Papers API, Kaggle API, Gemini Deep Research |

---

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- Docker (for Redis)

### 1. Clone & Setup

```bash
git clone https://github.com/developwho/da-system.git
cd da-system

# Python environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Frontend dependencies
cd frontend/da-insights-hub
npm install
cd ../..
```

### 2. Configure Environment

```bash
cp .env.example .env
```

Edit `.env` with your API keys:

```env
GOOGLE_API_KEY=your-google-api-key      # Required (primary LLM)
OPENAI_API_KEY=your-openai-key          # Optional (fallback)
ANTHROPIC_API_KEY=your-anthropic-key    # Optional (fallback)
HUGGINGFACE_TOKEN=your-hf-token         # For paper search
KAGGLE_USERNAME=your-username            # For solution search
KAGGLE_KEY=your-kaggle-key
```

### 3. Start Services

```bash
# Terminal 1: Redis (required)
docker run -d -p 6379:6379 --name redis-da redis:7-alpine

# Terminal 2: Backend
uvicorn app.main:app --reload --port 8000

# Terminal 3: Frontend
cd frontend/da-insights-hub
npm run dev
```

Open **http://localhost:8080** and start analyzing.

> **Demo Mode:** Set `VITE_USE_MOCK=true` in `frontend/da-insights-hub/.env.development` to explore the UI with mock data (no backend required).

### Optional Services

```bash
# Celery worker (async task processing)
celery -A app.tasks.celery_app worker --loglevel=info --pool=solo

# MLflow UI (experiment dashboard)
mlflow ui --backend-store-uri file:./mlruns
# http://localhost:5000
```

---

## API Reference

### Chat & Sessions

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/chat/sessions` | Create a new chat session |
| `POST` | `/api/v1/chat/sessions/{id}/messages` | Send a message |
| `GET` | `/api/v1/chat/sessions/{id}` | Get session details |
| `GET` | `/api/v1/chat/sessions` | List all sessions |
| `WS` | `/api/v1/chat/ws/{id}` | Real-time WebSocket connection |

### Data Management

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/data/upload` | Upload CSV/Excel file |
| `GET` | `/api/v1/data/{id}/profile` | Get data profile & statistics |
| `GET` | `/api/v1/data/{id}/preview` | Preview data rows |

### Models & Analysis

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/analysis/train` | Start training pipeline |
| `GET` | `/api/v1/analysis/tasks/{id}` | Check task status |
| `GET` | `/api/v1/models/{id}` | Get model details |
| `POST` | `/api/v1/models/{id}/predict` | Run predictions |
| `GET` | `/api/v1/models/{id}/explain` | Get SHAP explanations |

### Reports

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/reports/{id}` | Get Markdown report |
| `GET` | `/api/v1/reports/{id}/html` | Get HTML dashboard |
| `GET` | `/api/v1/reports/{id}/download` | Download report file |

> Full interactive API docs available at **http://localhost:8000/docs** (Swagger UI)

---

## Project Structure

```
da-system/
├── app/
│   ├── agents/                # AI Agent system
│   │   ├── base.py            # BaseAgent with async event emission
│   │   ├── orchestrator.py    # Workflow state machine
│   │   ├── contracts.py       # Inter-agent data normalization
│   │   ├── problem_definition.py
│   │   ├── modeling.py        # FLAML AutoML wrapper
│   │   ├── insight.py         # SHAP + LLM analysis
│   │   ├── reporting.py       # Report generation
│   │   ├── report_template.py # McKinsey-style HTML template
│   │   └── research/          # Literature review agents (3)
│   ├── api/routes/            # REST + WebSocket endpoints
│   ├── core/
│   │   ├── data_pipeline/     # Loader, validation, profiling
│   │   ├── automl/            # FLAML configuration
│   │   └── evaluation/        # SHAP analysis
│   ├── services/
│   │   ├── llm/               # Multi-provider LLM router
│   │   └── external/          # HuggingFace, Kaggle, DeepResearch
│   ├── storage/               # Redis sessions, file manager, MLflow
│   └── tasks/                 # Celery async tasks
├── frontend/da-insights-hub/
│   └── src/
│       ├── components/        # React components (chat, progress, sidebar)
│       ├── pages/             # Data, Models, Reports, Chat pages
│       ├── services/          # API clients + adapters
│       ├── hooks/             # React Query hooks
│       └── lib/               # WebSocket client, config
├── data/                      # User uploads (gitignored)
├── outputs/                   # Generated reports & models (gitignored)
└── mlruns/                    # MLflow experiment data (gitignored)
```

---

## How It Works

```
1. Upload        User uploads a CSV or Excel file
                  ↓
2. Profiling     System profiles data: types, distributions, missing values,
                  skewness, outliers, class imbalance
                  ↓
3. Q&A           AI asks domain-specific questions based on data intelligence
                  (e.g., outlier handling strategy, analysis goals)
                  ↓
4. Planning      System generates an analysis plan for user confirmation
                  ↓
5. Research      Parallel literature review across 3 sources
                  ↓
6. Modeling      FLAML AutoML with research-informed model selection
                  7-step preprocessing: datetime → outliers → encoding →
                  missing values → near-zero variance → stratified split
                  ↓
7. Insights      SHAP feature importance, effect sizes, error analysis
                  ↓
8. Report        McKinsey-quality HTML report with executive summary,
                  methodology, KPI cards, and actionable recommendations
```

---

## License

[MIT](LICENSE)
