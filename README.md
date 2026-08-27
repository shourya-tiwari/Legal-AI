
# Legal Demystifier

Website URL: https://plainspeakai.onrender.com/

Legal contracts are often written in complex jargon, making them difficult for non-lawyers to understand. Our project simplifies this process by providing an AI-powered platform that:

- Uploads and analyzes legal documents

- Simplifies clauses into easy-to-read language

- Generates a timeline of key contract dates and obligations

- Scans for risks using predefined rules and contextual AI detection, then visualizes them in a risk radar (spider chart)

- Allows quick Q&A so users can ask questions about the contract in plain English

This tool is designed to empower individuals and businesses by making legal documents more transparent, accessible, and less intimidating.
## Tech Stack

**Client:** HTML, CSS, JavaScript

**Server:** Python, FastAPI, Uvicorn


## API Reference

#### upload document

```http
  POST /api/upload
```

| Parameter | Type     | Description                |
| :-------- | :------- | :------------------------- |
| `file` | `file` | **Required**. contract document file |

Response (JSON):
{
  "document_id": 1,
  "filename": "contract.pdf",
  "full_text": "This Agreement is made on..."
}


#### rewrite document

```http
  POST /api/rewrite
```

| Body Field | Type     | Description                       |
| :-------- | :------- | :-------------------------------- |
| `text`      | `string` | **Required**. "advanced" for legally literate |
| `mode`      | `string` | **Required**. "layman" for simplified mode |

Response (JSON):
{
  "rewritten_text": "This contract means..."
}


#### generate timeline

```http
  POST /api/map
```
| Body Field | Type     | Description                       |
| :-------- | :------- | :-------------------------------- |
| `contract_text` | `string` | **Required**. Full contract text |

Response (JSON):
{
  "timeline": [
    { "date_description": "Start Date", "event": "Agreement begins on Jan 1, 2025" },
    { "date_description": "End Date", "event": "Contract ends on Dec 31, 2025" }
  ]
}


#### risk scan 

```http
  POST /api/risk/scan
```
| Body Field | Type     | Description                      |
| :--------- | :------- | :------------------------------- |
| `text`     | `string` | **Required.** Full contract text |

Response (JSON):
{
  "flagged_clauses": [
    {
      "clause": "The tenant shall indemnify the landlord...",
      "keyword_flags": [
        { "term": "indemnify", "predefined_explanation": "Potential liability concern" }
      ],
      "contextual_flags": [
        { "term": "penalty", "explanation": "May indicate financial risk" }
      ]
    }
  ],
  "risk_summary": "2 high-risk terms detected: 1 keyword-based, 1 contextual."
}



#### ask a question

```http
  POST /api/ask
```
| Body Field      | Type     | Description                                  |
| :-------------- | :------- | :------------------------------------------- |
| `contract_text` | `string` | **Required.** Full contract text             |
| `question`      | `string` | **Required.** Question to ask about contract |

Response (JSON):
{
  "answer": "The contract can be terminated with 30 days' notice."
}


#### structured clause analysis

```http
  POST /api/nlp/analyze
```
| Body Field | Type | Description |
| :-- | :-- | :-- |
| `contract_text` | `string` | **Required.** Full contract text |
| `use_ai_escalation` | `boolean` | Optional, default `false`. If true, clauses the rule-based classifiers can't confidently handle are escalated to Gemini. |

Breaks the contract into clauses and annotates each with its type, deontic tags (obligation/permission/prohibition/discretion), defined terms used, cross-references, money/jurisdiction entities, and dates. Runs entirely offline (rule-based) unless `use_ai_escalation` is set.

Response (JSON):
{
  "clauses": [
    {
      "id": 1,
      "text": "The Tenant shall pay a security deposit within 30 days.",
      "clause_type": "other",
      "clause_type_source": "rule",
      "deontic_tags": [{ "modality": "obligation", "trigger_phrase": "shall", "source": "rule" }],
      "temporal_expressions": [{ "text": "30 days", "normalized_date": null }]
    }
  ]
}


## Environment Variables

The backend reads its configuration from `backend/.env` (see `backend/app/config.py`):

| Variable | Required | Description |
| :-- | :-- | :-- |
| `GOOGLE_API_KEY` | Yes | API key for the Gemini Developer API (`google-genai`). Get one from Google AI Studio. |
| `GENAI_MODEL` | No | Gemini model name. Defaults to `gemini-flash-latest` if unset. |
| `DATABASE_URL` | No | SQLAlchemy connection string. Defaults to a local SQLite file (`sqlite:///./legalai.db`) — zero setup needed. Point at Postgres with `postgresql+psycopg://user:pass@host:5432/db` (see `docker-compose.yml`). |
| `REDIS_URL` | No | Redis connection string for rate limiting, e.g. `redis://localhost:6379/0`. Leave unset/empty to disable rate limiting entirely. |
| `AUTH_REQUIRED` | No | `true`/`false`, defaults to `false`. When off, every request resolves to a shared "default" org and no API key is needed — this is what keeps the public frontend working today. Flip to `true` once you've issued API keys (see below) to require `Authorization: Bearer <key>` on every `/api/*` call. |
| `RATE_LIMIT_PER_MINUTE` | No | Requests/minute per org (or per client IP when `AUTH_REQUIRED` is off). Defaults to `60`. |



## Run Locally

Clone the project

```bash
  git clone https://github.com/kavvyaaaa/LegalDemystifier.git
```

Go to the project directory

```bash
  cd LegalDemystifier
```

**Backend Setup**

- (Optional) Start Postgres + Redis for local dev with Docker:
```bash
    docker compose up -d
```
Without this, the backend falls back to a local SQLite file and disables rate limiting automatically — Docker is not required to run the app.

- Create and activate a virtual environment (recommended), from the `backend/` directory:
```bash
    cd backend
    python -m venv venv
    source venv/Scripts/activate   # On Windows (Git Bash); use venv\Scripts\activate in cmd/PowerShell
```
Install dependencies

```bash
    pip install -r requirements.txt
```

Create `backend/.env` with your `GOOGLE_API_KEY` (see Environment Variables above), then start the server:

```bash
    uvicorn app.main:app --reload
```
The backend will run at: http://127.0.0.1:8000

Run the backend test suite:

```bash
    pytest
```

**Frontend Setup**
- Open `frontend/index.html` directly in your browser, or use a simple local server:

```http
    npx serve frontend
```
Frontend will be available at: http://localhost:3000 (if using server)

By default, `frontend/app.js` points at the deployed production API
(`https://plainspeak-ai.onrender.com/api`), configured in `frontend/config.js`.
To point the frontend at your local backend instead, either edit
`PRODUCTION_BASE_URL` in `frontend/config.js`, or open the page with an `api`
query parameter, e.g. `index.html?api=http://127.0.0.1:8000/api` — no source
edit required, and the local backend's CORS config already allows any origin.

**Issuing API keys** (only needed once you set `AUTH_REQUIRED=true`):
```bash
    python scripts/create_api_key.py "My Org" "my-key-name"
```
Prints the raw key once — save it, only its hash is stored. Send it as `Authorization: Bearer <key>` on every `/api/*` request.

## Authors

- [@Shashquatch28](https://github.com/Shashquatch28)
- [@kavvyaaaa](https://github.com/kavvyaaaa)
- [@shourya-tiwari](https://github.com/shourya-tiwari)

