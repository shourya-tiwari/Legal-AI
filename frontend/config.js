// Backend API base URL.
//
// Defaults to the deployed production API. For local development against a
// backend running via `uvicorn app.main:app --reload` (http://127.0.0.1:8000),
// either edit PRODUCTION_BASE_URL below to point at localhost, or open this
// page with `?api=http://127.0.0.1:8000/api` appended to the URL to override
// it without editing source.
window.LEGALAI_CONFIG = (function () {
  const PRODUCTION_BASE_URL = "https://plainspeak-ai.onrender.com/api";

  const params = new URLSearchParams(window.location.search);
  const override = params.get("api");

  return {
    baseURL: override || PRODUCTION_BASE_URL,
  };
})();
