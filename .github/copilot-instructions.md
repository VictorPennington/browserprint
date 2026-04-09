# BrowserPrint Copilot Instructions

## App Purpose
BrowserPrint is a local desktop companion app (BeeWare/Toga) that exposes a local HTTP API so browser-based systems can send print jobs without opening print dialog windows.

## Current Functionality
- Starts a local FastAPI server on `127.0.0.1:8003` when the desktop app launches.
- Accepts CORS requests from localhost origins used by local web apps.
- Provides `POST /print` to receive a Base64-encoded PDF payload.
- Saves received PDF files to a desktop debug folder (`~/Desktop/debug_pdfs`).
- Calls SumatraPDF in silent print mode using the provided printer command.

## Current Scope
- Optimized for local-machine printing workflows.
- Focuses on practical reliability and minimal UI, with the API doing the core work.

## Development Direction
When editing this project:
- Prefer small, low-risk changes.
- Keep API behavior stable unless explicitly requested.
- Preserve compatibility with the existing BeeWare app startup flow.
- Validate changes with tests or local verification whenever possible.
