# Nexus CMO

## The Autonomous Marketing Intelligence Layer

> Transform marketing from manual workflows into a continuously improving autonomous system.

---

## Vision

Nexus CMO is not another content generator. It's an **AI-powered Chief Marketing Officer** — a self-hosted, multi-agent system that discovers what matters, decides what to say, creates branded content, validates it, publishes it, and learns from the results.

```mermaid
graph LR
    A["Discover"] --> B["Decide"]
    B --> C["Create"]
    C --> D["Review"]
    D --> E["Publish"]
    E --> F["Learn"]
    F -.-> A
    
    style A fill:#2563eb,stroke:#1e40af,color:#fff
    style B fill:#7c3aed,stroke:#6d28d9,color:#fff
    style C fill:#db2777,stroke:#be185d,color:#fff
    style D fill:#ea580c,stroke:#c2410c,color:#fff
    style E fill:#16a34a,stroke:#15803d,color:#fff
    style F fill:#0891b2,stroke:#0e7490,color:#fff
```

---

## The Problem Marketing Teams Face

| Traditional Workflow | Nexus CMO |
|---|---|
| Scattered tools for each task | Unified intelligence layer |
| Manual trend discovery | Autonomous signal detection |
| Disconnected approval workflows | Integrated validation gates |
| Repetitive multi-platform publishing | Intelligent distribution |
| Analytics in separate dashboards | Closed-loop performance feedback |

---

## Architecture

Nexus CMO uses a **specialized multi-agent architecture** where each stage of the marketing lifecycle has its own intelligence.

```mermaid
graph TB
    UI["Dashboard & Control"]
    API["FastAPI Orchestrator"]
    
    subgraph Intelligence["Intelligence Layer"]
        Scout["Scout Agent<br/>Discovers signals"]
        Planner["Planner Agent<br/>Strategizes approach"]
        Creator["Creator Agent<br/>Generates content"]
    end
    
    subgraph Execution["Execution Layer"]
        Reviewer["Reviewer Agent<br/>Validates quality"]
        Publisher["Publisher Agent<br/>Distributes content"]
        Analyst["Analyst Agent<br/>Measures performance"]
    end
    
    Platforms["Platform Integrations"]
    
    UI --> API
    API --> Scout
    API --> Planner
    API --> Creator
    Scout -.->|Intelligence| Planner
    Planner -.->|Strategy| Creator
    Creator --> Reviewer
    Reviewer --> Publisher
    Publisher --> Platforms
    Platforms --> Analyst
    Analyst -.->|Insights| Scout
    
    style UI fill:#f0f9ff,stroke:#0284c7,color:#0c4a6e
    style API fill:#f0f9ff,stroke:#0284c7,color:#0c4a6e
    style Intelligence fill:#dcfce7,stroke:#16a34a,color:#15803d
    style Execution fill:#fef3c7,stroke:#d97706,color:#92400e
    style Scout fill:#dbeafe,stroke:#0284c7
    style Planner fill:#dbeafe,stroke:#0284c7
    style Creator fill:#dbeafe,stroke:#0284c7
    style Reviewer fill:#fde68a,stroke:#d97706
    style Publisher fill:#fde68a,stroke:#d97706
    style Analyst fill:#fde68a,stroke:#d97706
    style Platforms fill:#fccf8f,stroke:#ea580c,color:#fff
```

---

## The Six Agents

### Scout
Continuously monitors signals worth acting on:
- AI & technology news
- RSS feeds & Hacker News
- GitHub activity & emerging topics
- Industry trends

### Planner
Evaluates signals and decides:
- What deserves attention
- Which audience to target
- Platform selection
- Content format & timing

### Creator
Transforms strategy into production-ready content:
- Platform-specific adaptations
- Brand-consistent messaging
- Visual asset generation
- Optimized CTAs & hashtags

### Reviewer
Quality & safety validation gate:
- Brand voice consistency
- Claim verification
- Credential protection
- Platform suitability
- Risk assessment

### Publisher
Handles multi-platform distribution:
- LinkedIn, X, Facebook, Instagram
- Discord, Reddit, Medium, Substack
- Email platforms (Brevo, MailerLite)
- Webhook integrations

### Analyst
Closes the intelligence loop:
- Performance tracking
- Insight generation
- Strategy recommendations
- Continuous optimization

---

## The Workflow

```mermaid
sequenceDiagram
    participant Scout
    participant Planner
    participant Creator
    participant Reviewer
    participant Publisher
    participant Platforms
    participant Analyst

    Scout->>Planner: Signal detected
    Planner->>Creator: Strategy defined
    Creator->>Reviewer: Content ready
    Reviewer->>Reviewer: Validate quality
    alt Approved
        Reviewer->>Publisher: Clear to publish
        Publisher->>Platforms: Distribute content
        Platforms->>Analyst: Performance data
        Analyst->>Scout: Insights for next cycle
    else Rejected
        Reviewer->>Creator: Revision needed
        Creator->>Reviewer: Updated content
    end
```

---

## Brand Intelligence

Nexus CMO maintains a **Brand Kit** that acts as a shared context layer across all agents:

```mermaid
graph TB
    Brand["Brand Configuration"]
    
    subgraph Identity["Visual Identity"]
        Logo["Logo & Colors"]
        Type["Typography"]
    end
    
    subgraph Voice["Brand Voice"]
        Tone["Tone & Style"]
        Messaging["Core Messages"]
        CTA["Calls to Action"]
    end
    
    subgraph Rules["Content Rules"]
        Forbidden["Forbidden Styles"]
        Hashtags["Hashtag Strategy"]
        Products["Product URLs"]
    end
    
    Brand --> Identity
    Brand --> Voice
    Brand --> Rules
    
    Identity & Voice & Rules --> AI["AI Content Generation"]
    AI --> Output["Brand-Consistent Output"]
    
    style Brand fill:#6366f1,color:#fff
    style AI fill:#a855f7,color:#fff
    style Output fill:#ec4899,color:#fff
```

---

## Technology Stack

```mermaid
graph LR
    subgraph Backend["Backend"]
        Python["Python 3"]
        FastAPI["FastAPI"]
        SQLite["SQLite"]
        APScheduler["APScheduler"]
    end
    
    subgraph AI["AI & Inference"]
        Ollama["Ollama (Local)"]
        OpenAI["OpenAI API"]
        Anthropic["Anthropic API"]
        Gemini["Google Gemini API"]
    end
    
    subgraph Automation["Automation & Creative"]
        Playwright["Playwright"]
        Pillow["Pillow"]
        FFmpeg["FFmpeg"]
        HeyGen["HeyGen API"]
    end
    
    subgraph Frontend["Frontend"]
        React["React"]
        Dashboard["Interactive Dashboard"]
    end
    
    subgraph Security["Security"]
        Encryption["Fernet Encryption"]
        Logging["Audit Logging"]
        Gates["Approval Gates"]
    end
    
    style Backend fill:#3b82f6,color:#fff
    style AI fill:#8b5cf6,color:#fff
    style Automation fill:#ec4899,color:#fff
    style Frontend fill:#f59e0b,color:#fff
    style Security fill:#10b981,color:#fff
```

---

## Quick Start

### Prerequisites
- Python 3.8+
- pip
- Playwright & Chromium
- Ollama or API keys (OpenAI/Anthropic/Gemini)

### Installation

**1. Clone the repository**
```bash
git clone https://github.com/yourusername/Nexus-CMO.git
cd Nexus-CMO
```

**2. Setup Python environment**
```bash
cd backend
python3 -m venv .venv

# macOS / Linux
source .venv/bin/activate

# Windows
.venv\Scripts\activate
```

**3. Install dependencies**
```bash
pip install -r requirements.txt
playwright install chromium
```

**4. Configure environment**
```bash
cp .env.example .env
```

Edit `.env` with your settings:
```env
# AI Provider
AI_PROVIDER=ollama
OLLAMA_URL=http://127.0.0.1:11434
OLLAMA_MODEL=qwen3:8b

# Alternative: Cloud providers
# OPENAI_API_KEY=sk_...
# ANTHROPIC_API_KEY=sk_ant_...
# GEMINI_API_KEY=...

# Settings
HEADLESS=false
```

**5. Start the system**
```bash
python main.py
```

Dashboard: `http://localhost:8000`  
API Docs: `http://localhost:8000/docs`

---

## Local AI Setup

For completely private operation with **Ollama**:

```bash
# Install and start Ollama
ollama serve

# In another terminal, pull the model
ollama pull qwen3:8b

# Set in .env
AI_PROVIDER=ollama
```

No external API keys, no data leaving your infrastructure.

---

## API Endpoints

```mermaid
graph LR
    GET1["GET /api/health"]
    POST1["POST /api/pipeline/run"]
    GET2["GET /api/pipeline/status"]
    GET3["GET /api/pipeline/queue"]
    POST2["POST /api/pipeline/approve/:id"]
    POST3["POST /api/pipeline/reject/:id"]
    
    GET4["GET /api/pipeline/signals"]
    GET5["GET /api/pipeline/analytics"]
    GET6["GET /api/brand/config"]
    PUT1["PUT /api/brand/config"]
    
    POST1 -.-> GET2
    GET2 -.-> GET3
    GET3 -.-> POST2 & POST3
    GET4 -.-> GET5
    GET6 -.-> PUT1
    
    style GET1 fill:#10b981
    style POST1 fill:#3b82f6
    style GET2 fill:#10b981
    style GET3 fill:#10b981
    style POST2 fill:#f59e0b
    style POST3 fill:#ef4444
    
    classDef endpoint fill:#e0e7ff,stroke:#818cf8
    class GET4,GET5,GET6,PUT1 endpoint
```

**Interactive API Explorer**: Visit `/docs` after starting the server.

---

## Execution Timeline

```mermaid
timeline
    title Daily Nexus CMO Autonomous Execution
    
    section Morning
    08:00 : Scout discovers new signals
         : Planner identifies opportunities
    11:00 : Creator generates content
         : Reviewer validates

    section Afternoon
    14:00 : Scout refreshes intelligence
    
    section Evening
    23:00 : Publisher distributes approved content
    23:30 : Analyst generates insights

    section Next Day
    Loop : Better intelligence to better decisions
```

---

## Project Structure

```
Nexus-CMO/
├── backend/
│   ├── agents/
│   │   ├── scout/          # Signal discovery
│   │   ├── planner/        # Strategy & planning
│   │   ├── creator/        # Content generation
│   │   ├── reviewer/       # Quality validation
│   │   ├── publisher/      # Distribution
│   │   └── analyst/        # Performance tracking
│   │
│   ├── api/                # FastAPI routes
│   ├── services/           # Business logic
│   ├── integrations/       # Platform APIs
│   ├── models/             # Data models
│   └── main.py             # Entry point
│
├── frontend/
│   └── dashboard/          # React UI
│
├── configs/
│   └── brand.yaml          # Brand configuration
│
├── .env.example            # Environment template
├── requirements.txt        # Python dependencies
└── README.md
```

---

## Security by Design

- **Credential Protection** — Platform credentials encrypted & stored locally  
- **Approval Gates** — Content validated before publication  
- **Claim Validation** — Problematic claims flagged automatically  
- **Local-First** — Sensitive data remains on your infrastructure  
- **Audit Logging** — All actions tracked for compliance  

**Philosophy**: *Let AI move fast. Keep the system accountable.*

---

## Roadmap

### Intelligence Expansion
- Deeper competitor analysis
- Market opportunity detection
- Predictive content performance
- Share-of-voice tracking

### New Agents
- SEO Agent
- Community Agent
- Outreach Agent
- Campaign Agent
- Growth Agent

### Enhanced Execution
- Campaign-level orchestration
- Automated A/B testing
- Adaptive publishing schedules
- Cross-platform synchronization

### Advanced Analytics
- Attribution modeling
- Audience segmentation
- Content performance prediction
- Automated strategy recommendations

---

## Design Philosophy

```mermaid
graph TB
    A["Intelligence<br/>before execution"]
    B["Specialization<br/>before generalization"]
    C["Autonomy<br/>with boundaries"]
    D["Learning<br/>over repetition"]
    
    A --> Core["Nexus CMO<br/>Core Principles"]
    B --> Core
    C --> Core
    D --> Core
    
    Core --> Result["Autonomous<br/>Marketing Intelligence"]
    
    style A fill:#3b82f6,color:#fff
    style B fill:#8b5cf6,color:#fff
    style C fill:#ec4899,color:#fff
    style D fill:#f59e0b,color:#fff
    style Core fill:#10b981,color:#fff,stroke:#059669,stroke-width:3px
    style Result fill:#06b6d4,color:#fff
```

---

## Contributors

### Lakshya Dogra
**AI & Backend Architecture**

Responsible for the technical foundation and intelligent orchestration:
- Backend system design and FastAPI implementation
- Multi-agent architecture and orchestration
- AI provider integrations (Ollama, OpenAI, Anthropic, Google Gemini)
- Agent prompt engineering and performance optimization
- Pipeline testing and deployment strategy

### Vishesh Nigam
**Frontend & Product Experience**

Responsible for the user-facing platform and design execution:
- Interactive dashboard development and UI/UX
- Visual design and brand identity implementation
- Agent visualization and monitoring interface
- Animations and interactive components
- Frontend integration with backend APIs

---

## Built for Hackathon

Nexus CMO represents a fundamental shift in how AI can approach marketing:

**Not**: "How can AI help marketers?"  
**But**: "What if marketing itself could be autonomous?"

From the first signal to the final performance insight, every component is connected in a self-improving loop.

```mermaid
graph LR
    Start["Raw Signals"] 
    Start --> Process["Intelligent Processing"]
    Process --> Action["Strategic Execution"]
    Action --> Measure["Performance Measurement"]
    Measure --> Learn["Continuous Learning"]
    Learn --> Improve["Better Decisions"]
    Improve --> Start
    
    style Start fill:#0891b2,color:#fff
    style Process fill:#7c3aed,color:#fff
    style Action fill:#db2777,color:#fff
    style Measure fill:#ea580c,color:#fff
    style Learn fill:#16a34a,color:#fff
    style Improve fill:#2563eb,color:#fff
```

---

## License

MIT License — See LICENSE file for details.

---

## Acknowledgements

Nexus CMO builds upon the open-source **SocialFlow** foundation, extending its autonomous social-media architecture into a more polished, **AI Chief Marketing Officer experience** optimized for the hackathon.

---

<div align="center">

### From Marketing Tools to Marketing Intelligence

Discover • Decide • Create • Review • Publish • Learn

[Get Started](#quick-start) • [API Docs](#api-endpoints) • [Roadmap](#roadmap)

---

Built for autonomous marketing intelligence

</div>
