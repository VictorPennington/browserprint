# BrowserPrint Copilot Instructions

## App Purpose
BrowserPrint is a local desktop companion app (BeeWare/Toga) that exposes a local HTTP API so browser-based systems can send print jobs without opening print dialog windows.

## Runtime Architecture
- Toga app startup initializes the main log window, wires UI controllers, installs app log handlers, then starts the local FastAPI server in a daemon thread.
- FastAPI app is created in `browserprint/api/server.py` and mounted once with CORS middleware.
- API route handlers in `browserprint/api/routes.py` validate incoming jobs and enqueue them.
- A background download worker thread consumes an in-memory queue and fetches PDFs asynchronously.
- Logs from `browserprint.*` are mirrored to both the UI log panel and stdout.

## Current API Behavior
- Local API host/port defaults to `127.0.0.1:8003` (overridable with env vars).
- Exposed endpoints:
	- `GET /` returns a simple health-style payload.
	- `POST /print` validates one `{ pdfUrl, printCommand }` payload, enqueues it, and returns HTTP `202` with `requestId`.
	- `POST /print/jobs` validates a non-empty `jobs` array, enqueues each item, and returns HTTP `202` with batch `requestId` and `acceptedJobs`.
	- `OPTIONS /print` and `OPTIONS /print/jobs` are present for CORS preflight handling.
- Request acceptance is asynchronous: HTTP `202` only confirms validation and queueing, not successful download completion.
- `pdfUrl` must be `http://` or `https://`.
- Current route pipeline downloads and saves PDFs, but does not currently invoke Sumatra print execution from the route flow.
- `printCommand` is still required by schema and is logged/queued, but not executed by routes at this time.

## Auth, Download, and Configuration
- PDF fetch uses bearer authentication:
	- First from stored token (`AuthConfigStore`),
	- Then from `BROWSERPRINT_LARAVEL_TOKEN` fallback,
	- Otherwise download fails in background processing.
- Auth config defaults to `~/.browserprint/auth_config.json` (override with `BROWSERPRINT_CONFIG_DIR` and `BROWSERPRINT_CONFIG_FILE`).
- Token storage prefers OS keyring when available, with config-file fallback.
- Default output folder for downloaded PDFs is `~/Desktop/debug_pdfs` (override with `BROWSERPRINT_DEBUG_OUTPUT_DIR`).
- CORS defaults allow localhost/127.0.0.1 origins (including ports 8000 and 8003), methods `GET/POST/OPTIONS`, and headers `Content-Type/Authorization/X-CSRF-TOKEN`.

## Desktop UI Tools
- `Generate Bearer Token`:
	- Saves auth settings,
	- Generates Sanctum token,
	- Tests current session (`/api/browserprint/ping`),
	- Revokes token (`/api/browserprint/token/revoke`).
- `Make Request`:
	- Sends authenticated manual requests using saved base URL + token,
	- Supports `GET`, `POST`, `PUT`, `PATCH`, and `DELETE`.
- `Download PDF`:
	- Downloads an authenticated PDF from endpoint path or full URL,
	- Saves to the configured debug output directory.

## Current Scope
- Optimized for local-machine printing workflows.
- Focuses on practical reliability and minimal UI, with the local API and background download queue doing the core work.
- Current implementation is queue-and-download centric; print execution integration exists in codebase but is not yet active in route handling.

## Development Direction
When editing this project:
- Prefer small, low-risk changes.
- Keep API behavior stable unless explicitly requested.
- Preserve compatibility with the existing BeeWare app startup flow.
- Preserve current async acknowledgment semantics (`202 Accepted` before job completion) unless explicitly changed.
- Be explicit when changing auth/config/env behavior because desktop and API flows both depend on shared settings.
- Validate changes with tests or local verification whenever possible.
