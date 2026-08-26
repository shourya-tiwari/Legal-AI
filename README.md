
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


## Environment Variables

The backend reads its configuration from `backend/.env` (see `backend/app/config.py`):

| Variable | Required | Description |
| :-- | :-- | :-- |
| `GOOGLE_API_KEY` | Yes | API key for the Gemini Developer API (`google-genai`). Get one from Google AI Studio. |
| `GENAI_MODEL` | No | Gemini model name. Defaults to `gemini-flash-latest` if unset. |



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

## Authors

- [@Shashquatch28](https://github.com/Shashquatch28)
- [@kavvyaaaa](https://github.com/kavvyaaaa)
- [@shourya-tiwari](https://github.com/shourya-tiwari)

