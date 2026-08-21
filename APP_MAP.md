# BrowserPrint Application Map

## Quick Summary

BrowserPrint is a **local desktop companion app** (BeeWare/Toga) that exposes a local HTTP API so browser-based systems can send print jobs without opening print dialog windows.

### Core Flow
```
Browser/System → Local API (127.0.0.1:8003) → Download PDF → Save to Disk → PDFtoPrinter Silent Print
```

### Key Capabilities
- **Local API Server**: FastAPI server accepting print job requests via `POST /print` and `POST /print/jobs`
- **Two-Stage Pipeline**: Download worker thread → Print worker thread (both run perpetually in background)
- **Authentication**: Laravel Sanctum bearer token storage (OS keyring or config file fallback)
- **Desktop UI Tools**: Token management, manual requests, PDF downloads, settings inspection
- **Print Override Panel**: Disable printing entirely or substitute printer names for all jobs

---

## Application Architecture

### Startup Flow (`app.py`)

1. **Toga App Initialization**
   - Creates main window with log panel
   - Wires up `PrintOverridePanel` (disable printing switch + override input)
   - Installs app log handlers (logs go to UI panel + stdout)

2. **UI Controllers Setup**
   - `AuthSettingsController`: Token generation, session testing, revocation
   - `MakeRequestController`: Manual authenticated HTTP requests
   - `DownloadPdfController`: Manual PDF downloads from endpoints
   - `EnvSettingsController`: Read-only display of environment-driven settings

3. **Background Workers Start** (via `job_queue.py` import)
   - `_download_worker_thread`: Consumes `DOWNLOAD_QUEUE`, fetches PDFs, enqueues to `PRINT_QUEUE`
   - `_print_worker_thread`: Consumes `PRINT_QUEUE`, executes PDFtoPrinter silently

4. **FastAPI Server Starts** (daemon thread)
   - Runs on `127.0.0.1:8003` (configurable via env vars)
   - Handles incoming print job requests

---

## Component Paths & Responsibilities

### API Layer (`browserprint/api/`)

#### `server.py`
- **Purpose**: FastAPI app creation and middleware setup
- **Key Functions**:
  - `create_app()`: Builds FastAPI app with CORS middleware
  - `run_local_server()`: Starts uvicorn server
- **Middleware**:
  - CORS: Allows localhost/127.0.0.1 origins (ports 8000, 8003)
  - Request logging: Logs method, URL, status code, elapsed time
  - Validation error handler: Detailed JSON error responses

#### `routes.py`
- **Purpose**: HTTP endpoint definitions
- **Endpoints**:
  - `GET /`: Health check → `{"message": "hello world"}`
  - `POST /print`: Single job → validates `{pdfUrl, printerCommand, customerNumber?, invoiceNumber?}`, returns `202 Accepted` with `requestId`
  - `POST /print/jobs`: Batch jobs → validates `{jobs[], customerNumber?, invoiceNumber?}`, returns `202 Accepted` with batch `requestId`
  - `OPTIONS /print` & `/print/jobs`: CORS preflight handling
- **Job Enqueueing**: Pushes validated jobs to `DOWNLOAD_QUEUE` as tuples:
  ```python
  (request_id, pdf_url, printer_command, customer_number, invoice_number)
  ```

#### `job_queue.py`
- **Purpose**: Background worker threads and queue management
- **Queues**:
  - `DOWNLOAD_QUEUE`: Incoming jobs waiting for PDF download
  - `PRINT_QUEUE`: Downloaded PDFs waiting for print execution
- **Workers**:
  - `_download_worker()`: Infinite loop consuming `DOWNLOAD_QUEUE`
    - Calls `run_download_job()` to fetch and save PDF
    - If printing not disabled, enqueues to `PRINT_QUEUE`
  - `_print_worker()`: Infinite loop consuming `PRINT_QUEUE`
    - Calls `run_pdftoprinter_print()` to execute silent print
- **Thread Lifecycle**: Both workers are daemon threads started at module import

#### `download_service.py`
- **Purpose**: Download pipeline logic
- **Key Functions**:
  - `set_printing_disabled_provider(fn)`: Register callback to check if printing should be suppressed
  - `build_download_filename()`: Generates filename like `2026_08_13_1430_12345_INV001_documents.pdf`
  - `resolve_output_path()`: Handles filename collisions by appending `_2`, `_3`, etc.
  - `run_download_job()`: Main download orchestration
    - Creates output directory if needed
    - Calls `fetch_pdf()` from `pdf_fetcher.py`
    - Saves PDF bytes to disk
    - Conditionally enqueues to `PRINT_QUEUE` based on disable switch

#### `pdf_fetcher.py`
- **Purpose**: Authenticated PDF downloading
- **Token Resolution**:
  1. Try stored token from `AuthConfigStore`
  2. Fallback to `BROWSERPRINT_LARAVEL_TOKEN` env var
  3. Raise `PDFDownloadError` if neither available
- **Validation**:
  - Checks HTTP status codes (401/403 = auth failure, >=400 = error)
  - Validates content-type contains `application/pdf` OR content starts with `%PDF`
  - Enforces `MAX_PDF_BYTES` size limit
- **Key Function**: `fetch_pdf(url, token?)` → returns PDF bytes

#### `print_executor.py`
- **Purpose**: SumatraPDF command execution (legacy — retained for reference, no longer called by the worker)
- **Key Functions**:
  - `_parse_printer_command()`: Parses `printerCommand` string into argument list
    - Uses `shlex.split()` for proper shell-like parsing
    - Strips trailing `.pdf` filenames if present
    - **Shared** with `pdftoprinter_executor.py`
  - `run_sumatra_print(sumatra_path, printer_command, output_path)`: Executes Sumatra
    - Builds command: `[sumatra.exe, "-print-to", <parsed_args...>, <output_path>]`
    - Runs via `subprocess.run()` with `shell=False`
    - Raises `PrintExecutionError` on failure

#### `pdftoprinter_executor.py`
- **Purpose**: PDFtoPrinter (pdftoprinter-c) command execution — **active print backend**
- **Key Functions**:
  - `run_pdftoprinter_print(pdftoprinter_path, printer_command, output_path)`: Executes PDFtoPrinter
    - Reuses `_parse_printer_command()` from `print_executor.py`
    - Joins parsed printer tokens into a **single** argument (extra positionals would be read as more PDF files)
    - Builds command: `[PDFtoPrinter.exe, <output_path>, "<printer name>", "/s", "/no-autotray"]`
    - `/s` = silent, `/no-autotray` = don't pause on a missing paper size (unattended printing)
    - Runs via `subprocess.run()` with `shell=False`
    - Raises `PrintExecutionError` on failure
- **Vendor binaries**: `resources/vendor/pdftoprinter/PDFtoPrinter.exe` + `pdfium.dll` (DLL must sit beside the EXE)

#### `schemas.py`
- **Purpose**: Pydantic request validation models
- **Models**:
  - `PrintRequest`: Single job schema with `pdfUrl` (http/https required), `printerCommand` (required), optional `customerNumber`/`invoiceNumber`
  - `PrintJobsRequest`: Batch schema with `jobs[]` array (non-empty required), optional `customerNumber`/`invoiceNumber`

#### `sanctum_client.py`
- **Purpose**: Laravel Sanctum token lifecycle
- **Key Functions**:
  - `login(email, password, device_name)` → returns token
  - `test_session()` → validates current token
  - `revoke_token()` → invalidates token on server

#### `manual_request_client.py`
- **Purpose**: Manual authenticated HTTP requests (for testing)
- **Supports**: GET, POST, PUT, PATCH, DELETE
- **Uses**: Stored auth config for base URL + bearer token

---

### Authentication Layer (`browserprint/auth_*.py`)

#### `auth_config.py`
- **Purpose**: Persistent auth configuration and token storage
- **Classes**:
  - `AuthConfig`: Dataclass holding `api_base_url`, `email`, `device_name`, `token_present`, `token_storage`, etc.
  - `AuthConfigStore`: Manages reading/writing config to `~/.browserprint/auth_config.json`
    - Supports OS keyring for secure token storage
    - Falls back to config file if keyring unavailable
- **Config Location**: Overridable via `BROWSERPRINT_CONFIG_DIR` and `BROWSERPRINT_CONFIG_FILE` env vars

#### `auth_utils.py`
- **Purpose**: Auth-related utilities
- **Functions**:
  - `validate_base_url()`: Ensures URL is http/https and well-formed
  - `wrap_status_message()`: Formats status messages for UI display

---

### UI Layer (`browserprint/ui/`)

#### `log_panel.py` + `logging.py`
- **Purpose**: Application logging to UI
- **Features**:
  - `LogPanel`: Scrollable text area displaying log lines
  - `install_app_log_handler()`: Adds logger handler for `browserprint.*` modules
  - Logs mirrored to both UI panel and stdout

#### `auth_settings.py`
- **Purpose**: Token management UI
- **Tab**: "Token Config"
- **Features**:
  - Input fields: API Base URL, Email, Password, Device Name
  - Switch: "Replace existing token"
  - Buttons:
    - `Generate Bearer Token`: Saves config, calls Sanctum login, tests session
    - `Test Current Session`: Calls `/api/browserprint/ping`
    - `Revoke Token`: Calls `/api/browserprint/token/revoke`
  - Status output: Shows success/error messages

#### `make_request.py`
- **Purpose**: Manual HTTP request testing
- **Tab**: "Make Request"
- **Features**:
  - Displays saved API Base URL (read-only)
  - Input: Endpoint path or full URL
  - Input: HTTP method (GET, POST, PUT, PATCH, DELETE)
  - Multiline input: JSON payload (optional)
  - Button: `Send Request`
  - Status output: Response status code, headers, body

#### `download_pdf.py`
- **Purpose**: Manual PDF download testing
- **Tab**: "Download PDF"
- **Features**:
  - Displays saved API Base URL (read-only)
  - Input: PDF endpoint path or full URL
  - Button: `Download`
  - Status output: Success/failure message with saved file path
  - Saves to configured debug output directory (`~/Desktop/debug_pdfs`)

#### `print_override.py`
- **Purpose**: Runtime print control panel
- **Location**: Always visible above tab strip
- **Features**:
  - Switch: "Disable printing (download only)" → suppresses SumatraPDF execution
  - Button: "Open Download Folder" → opens Explorer to debug output directory
  - Switch: "Override print command" → enables text input
  - Text input: Substitute printer name for all incoming jobs
- **Integration**:
  - `get_override()` called by `routes.py` before enqueueing jobs
  - `is_printing_disabled()` called by `download_service.py` before enqueueing to `PRINT_QUEUE`

#### `env_settings.py`
- **Purpose**: Environment settings inspection
- **Tab**: "Settings"
- **Features**:
  - Opens separate window showing all env-driven settings:
    - API host/port
    - SumatraPDF path
    - Debug output directory
    - Config paths
    - Timeouts
    - Allowed origins
  - All values read-only (for debugging/reference)

---

### Configuration & Settings (`browserprint/settings.py`)

All configurable via environment variables:

| Setting | Env Var | Default |
|---------|---------|---------|
| API Host | `BROWSERPRINT_LOCAL_API_HOST` | `127.0.0.1` |
| API Port | `BROWSERPRINT_LOCAL_API_PORT` | `8003` |
| PDFtoPrinter Path | `BROWSERPRINT_PDFTOPRINTER_PATH` | `<bundled>/pdftoprinter/PDFtoPrinter.exe` |
| SumatraPDF Path (legacy) | `BROWSERPRINT_SUMATRA_PATH` | `<bundled>/SumatraPDF-3.6-64.exe` |
| Debug Output Dir | `BROWSERPRINT_DEBUG_OUTPUT_DIR` | `~/Desktop/debug_pdfs` |
| Config Dir | `BROWSERPRINT_CONFIG_DIR` | `~/.browserprint` |
| Config File | `BROWSERPRINT_CONFIG_FILE` | `auth_config.json` |
| Download Timeout | `BROWSERPRINT_DOWNLOAD_TIMEOUT_SECONDS` | `30` |
| Max PDF Size | `BROWSERPRINT_MAX_PDF_BYTES` | `50MB` |
| Laravel Auth Header | `BROWSERPRINT_LARAVEL_AUTH_HEADER` | `Authorization` |
| Allowed Origins | `BROWSERPRINT_ALLOWED_ORIGINS` | `localhost, 127.0.0.1 (ports 8000, 8003)` |

---

## End-to-End Job Flow

### 1. HTTP Request Arrives
```
POST http://127.0.0.1:8003/print
{
  "pdfUrl": "https://example.com/api/documents/123",
  "printerCommand": "ZDesigner GK420d",
  "customerNumber": "CUST001",
  "invoiceNumber": "INV-2026-001"
}
```

### 2. Route Handler (`routes.py`)
- Validates request against `PrintRequest` schema
- Checks `PrintOverridePanel.get_override()` for printer substitution
- Generates unique `requestId` (UUID hex)
- Enqueues to `DOWNLOAD_QUEUE`:
  ```python
  DOWNLOAD_QUEUE.put((request_id, pdf_url, effective_command, customer_number, invoice_number))
  ```
- Returns `202 Accepted` immediately (async acknowledgment)

### 3. Download Worker (`job_queue.py` → `download_service.py`)
- Consumes from `DOWNLOAD_QUEUE` in infinite loop
- Calls `run_download_job()`:
  1. Creates output directory if needed
  2. Generates filename: `2026_08_13_1430_CUST001_INV-2026-001_documents.pdf`
  3. Calls `fetch_pdf(pdf_url)` from `pdf_fetcher.py`
     - Resolves bearer token from `AuthConfigStore` or env var
     - Downloads PDF with authentication headers
     - Validates response (status code, content-type, size)
  4. Saves PDF bytes to disk
  5. Checks `is_printing_disabled()`:
     - If **disabled**: Logs success, stops here
     - If **enabled**: Enqueues to `PRINT_QUEUE`: `(request_id, output_path, printer_command)`

### 4. Print Worker (`job_queue.py` → `pdftoprinter_executor.py`)
- Consumes from `PRINT_QUEUE` in infinite loop
- Calls `run_pdftoprinter_print()`:
  1. Verifies PDFtoPrinter executable exists
  2. Parses `printer_command` and joins tokens into a single printer-name argument
  3. Builds command: `[PDFtoPrinter.exe, "<output_path>", "ZDesigner GK420d", "/s", "/no-autotray"]`
  4. Executes via `subprocess.run()` with `shell=False`
  5. Logs success or raises `PrintExecutionError` on failure

---

## Desktop UI Tools Workflow

### Generate Bearer Token (Token Config Tab)
1. User enters: API Base URL, Email, Password, Device Name
2. Clicks `Generate Bearer Token`
3. App saves config to `AuthConfigStore`
4. Calls Sanctum `/sanctum/csrf-cookie` then `/login`
5. Stores token in OS keyring (or config file fallback)
6. Tests session via `/api/browserprint/ping`
7. Logs outcome to UI panel

### Make Manual Request (Make Request Tab)
1. User enters: Endpoint path, HTTP method, optional JSON payload
2. Clicks `Send Request`
3. App constructs full URL from saved base URL + endpoint
4. Sends authenticated request with bearer token
5. Displays response status, headers, body in status output

### Download PDF Manually (Download PDF Tab)
1. User enters: PDF endpoint path or full URL
2. Clicks `Download`
3. App resolves full URL, calls `fetch_pdf()`
4. Saves to debug output directory with timestamped filename
5. Displays success message with file path

### Control Printing (PrintOverridePanel)
- **Disable printing**: Toggle switch → all jobs download but don't print
- **Override printer**: Enable switch + enter printer name → substitutes for all jobs
- **Open folder**: Button → launches Windows Explorer to debug output directory

---

## Error Handling Strategy

### API Layer
- **Validation errors**: Return `422 Unprocessable Entity` with detailed JSON error list
- **Missing token**: Log error, job fails in background (HTTP already returned `202`)
- **Download failures**: Logged with `request_id`, no HTTP retry (fire-and-forget model)
- **Print failures**: Logged with `request_id`, Sumatra stderr captured

### UI Layer
- **Network errors**: Display wrapped status messages in UI panels
- **Auth failures**: Show specific error (401/403) with guidance
- **Config errors**: Fall back to defaults, log warnings

---

## Development Notes

### Testing
- Tests in `tests/` directory use pytest
- Mock workers avoid actual network/printer calls
- Use `.env` file for local configuration overrides

### Extending
- **Add new endpoints**: Define in `routes.py`, add Pydantic schemas in `schemas.py`
- **Modify pipeline**: Edit `download_service.py` or `print_executor.py`
- **Add UI features**: Create new controller in `ui/`, add to `OptionContainer` in `app.py`
- **Change defaults**: Update `settings.py` and document env var overrides

### Constraints
- **Local-only**: API binds to `127.0.0.1` by design (no external access)
- **Async acknowledgment**: HTTP `202` confirms queueing, not completion
- **Single-instance**: No built-in multi-instance support
- **Windows-focused**: PDFtoPrinter (and legacy SumatraPDF) are Windows-specific (paths configurable)

---

## Change Log

### 2026-08-21 — Switched print backend from SumatraPDF to PDFtoPrinter (pdftoprinter-c)

**Goal**: Replace SumatraPDF with [pdftoprinter-c](https://github.com/emendelson/pdftoprinter-c) as the print engine, for testing.

**Actions taken**:
1. **Security review** (subagent, static source review of `pdftoprinter.c`, `build.bat`, manifest, `app.rc`):
   - Verdict: *safe with caveats* — no network code, no shell/process execution (no command-injection surface), no telemetry, runs as `asInvoker`, ASLR/DEP enabled.
   - Caveats: release binaries are author-built (not reproducible from source); `pdfium.dll` is an implicit import → keep the vendor folder non-writable by others (DLL sideloading); build script downloads PDFium without checksum verification (only relevant if rebuilding).
2. **Vendored binaries**: `PDFtoPrinter.exe` + `pdfium.dll` placed in `resources/vendor/pdftoprinter/` (DLL must sit beside the EXE).
3. **New executor**: `api/prints/pdftoprinter_executor.py` with `run_pdftoprinter_print()`:
   - Reuses `PrintExecutionError` and `_parse_printer_command()` from `executor.py`.
   - Command: `[PDFtoPrinter.exe, <pdf>, "<printer name>", "/s", "/no-autotray"]` — printer name joined into one argument (extra positionals would be parsed as more PDF files).
4. **Wiring**:
   - `settings.py`: added `PDFTOPRINTER_PATH` (env `BROWSERPRINT_PDFTOPRINTER_PATH`, default `<bundled>/pdftoprinter/PDFtoPrinter.exe`).
   - `job_queue.py`: `_print_worker()` now calls `run_pdftoprinter_print()` instead of `run_sumatra_print()`.
   - `api/prints/__init__.py`: docstring updated.
5. **Tests**:
   - New `tests/test_pdftoprinter_executor.py` (4 tests: command shape, unquoted-name joining, failure, missing exe).
   - `tests/test_routes.py`: all monkeypatch targets updated from `job_queue.run_sumatra_print` → `job_queue.run_pdftoprinter_print`.
   - Full suite: **63 passed**.
6. **Legacy kept**: `api/prints/executor.py` (Sumatra) and `SUMATRA_PATH` setting remain in place but are no longer called by the worker — easy to revert if needed.

**To revert**: point `_print_worker()` back to `run_sumatra_print(_SUMATRA_PDF_PATH, ...)` and restore the `SUMATRA_PATH` import in `job_queue.py`.

---

## File Reference

| File | Purpose |
|------|---------|
| `app.py` | Toga app startup, UI wiring, server launch |
| `api/server.py` | FastAPI app creation, middleware |
| `api/routes.py` | HTTP endpoint handlers |
| `api/job_queue.py` | Background worker threads, queues |
| `api/download_service.py` | Download pipeline logic |
| `api/pdf_fetcher.py` | Authenticated PDF downloading |
| `api/prints/pdftoprinter_executor.py` | PDFtoPrinter command execution (active backend) |
| `api/prints/executor.py` | SumatraPDF command execution (legacy) |
| `api/schemas.py` | Pydantic request validation |
| `api/sanctum_client.py` | Laravel Sanctum token lifecycle |
| `api/manual_request_client.py` | Manual HTTP request testing |
| `auth_config.py` | Persistent auth config + token storage |
| `auth_utils.py` | Auth utilities (URL validation, messaging) |
| `settings.py` | Environment-driven configuration |
| `ui/log_panel.py` | Log display widget |
| `ui/logging.py` | App log handler installation |
| `ui/auth_settings.py` | Token management UI |
| `ui/make_request.py` | Manual request testing UI |
| `ui/download_pdf.py` | Manual PDF download UI |
| `ui/print_override.py` | Print control panel |
| `ui/env_settings.py` | Settings inspection window |
