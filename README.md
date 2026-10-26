# Tusalama Road Safety Management System

Tusalama is a Kenya-focused road-safety application for managing incident
reports, exploring hotspots, and supporting evidence-informed prevention.
It includes a responsive Flask web dashboard and retains the original
menu-driven Python application.

## Features

- Register, view, edit, and delete road incident reports.
- Assess incident risk with transparent, rule-based scoring and recommendations.
- Explore hotspot and trend charts with county, road, date, and severity filters.
- View incidents on a Leaflet/OpenStreetMap map; search Kenyan place names or
  select a point to populate coordinates.
- Forecast hotspot trends only when recent data is sufficient, and present
  evidence-linked suggestions for professional review.
- Optionally request OpenAI's review of historical hotspot projections,
  aggregate likely contributing factors, and possible safety actions; raw
  reports and coordinates are not sent to OpenAI.
- Optionally display configured public safety signals from Bluesky, the official
  X API, and approved Kenyan government RSS domains. Signals are unverified
  leads and are not automatically saved as incidents.
- Export reports as CSV, Excel, or PDF.
- Sign up as a road user or road-safety agency. Agencies need administrator
  approval; road users can access and manage their own reports.
- Create the first administrator account using a one-time login-page setup, or
  provision it from environment variables.
- Store accounts and incidents in SQLite and download database snapshots from
  the administrator panel.
- Use a Kenyan flag-inspired visual theme and mobile-friendly interface.

## Requirements

- Python 3.10 or later.
- Windows PowerShell, Command Prompt, or another terminal.
- Internet access for OpenStreetMap tiles, location lookup, and optional public
  signal sources.

## Install and run the web app (Windows PowerShell)

From the project directory:

```powershell
Set-Location -LiteralPath 'C:\path\to\ROAD SAFETY MANAGEMENT SYSTEM'
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Set a persistent Flask session-signing key. Keep it private and reuse it when
restarting the app; changing it signs out existing sessions:

```powershell
$key = [Environment]::GetEnvironmentVariable("FLASK_SECRET_KEY", "User")
if (-not $key) {
    $key = .\.venv\Scripts\python.exe -c "import secrets; print(secrets.token_urlsafe(48))"
    [Environment]::SetEnvironmentVariable("FLASK_SECRET_KEY", $key, "User")
}
$env:FLASK_SECRET_KEY = $key
```

### Create the administrator account

For an empty database, leave `ROAD_SAFETY_ADMIN_PASSWORD` unset and start the
app. Open [http://127.0.0.1:5000/login](http://127.0.0.1:5000/login), select
**Create administrator account**, and enter a username, email, and password of
at least 12 characters. This one-time setup is disabled after the first account
is created. Public signup does not allow administrator accounts.

Alternatively, configure the administrator in PowerShell **before** starting
the app. These variables apply only to processes started from that terminal:

```powershell
$env:ROAD_SAFETY_ADMIN_USERNAME = "admin"
$env:ROAD_SAFETY_ADMIN_EMAIL = "your-admin-email@example.com"
$env:ROAD_SAFETY_ADMIN_PASSWORD = "replace-with-a-new-unique-password"
```

Keep the password private and do not commit it. At startup, configured admin
credentials create or update the account in the selected database. If the
environment password is set, the first-admin setup link is not shown.

Start the dashboard in the same terminal used for configuration:

```powershell
.\.venv\Scripts\python.exe app.py
```

Open [http://127.0.0.1:5000](http://127.0.0.1:5000). To stop the server, focus
its terminal and press `Ctrl+C`. If port 5000 is occupied, stop the existing
Tusalama server before starting another instance.

### Database and incident data

By default, Tusalama uses `data/tusalama.sqlite3`. On first startup, it imports
the legacy `incidents.csv` once, retaining unique full records; subsequent
starts use SQLite and do not re-import CSV changes. Existing databases are
preserved. Set `TUSALAMA_DATABASE_PATH` before starting the app to use another
database file:

```powershell
$env:TUSALAMA_DATABASE_PATH = 'C:\secure-data\tusalama.sqlite3'
```

Download database snapshots from the administrator panel and keep backups in a
separate, access-controlled location. SQLite is local storage, not cloud
hosting; deploy with a managed database and suitable backup process if shared
remote storage is required.

### Optional public safety signal sources

Sources are disabled unless configured. Use environment variables in the same
terminal that starts the app:

```powershell
$env:TUSALAMA_BSKY_HANDLES = "official-handle.bsky.social"
$env:TUSALAMA_X_USER_IDS = "verified-account-id"
$env:TUSALAMA_X_BEARER_TOKEN = "your-private-api-token"
$env:TUSALAMA_RSS_FEEDS = "https://agency.go.ke/feed.xml"
```

Separate multiple Bluesky handles or X user IDs with commas, and separate RSS
feed URLs with semicolons. RSS endpoints must use HTTPS and approved Kenyan
government domains. Verify source ownership and comply with source terms before
enabling feeds. Treat returned posts as unverified reports; confirm them before
creating incident records. Do not commit API tokens or other credentials.

## Roles and access

| Role | Access |
| --- | --- |
| Administrator | Full incident, analytics, intelligence, account approval, and database-backup access. |
| Road safety agency | Incident and hotspot features after administrator approval; agency reports are scoped to that agency. |
| Road user | Submit, view, and manage their own reports and access their profile. |

Passwords are stored as hashes. Use HTTPS and a production WSGI server for
network deployments. Do not expose Flask's built-in development server to the
public internet. Set `FLASK_COOKIE_SECURE=1` when serving over HTTPS.

### Deploying on Render

The repository includes [render.yaml](./render.yaml) with the web service,
HTTPS cookie setting, generated session key, and a persistent disk mounted at
`/var/data`. The disk requires a Render service plan that supports persistent
disks and incurs the plan's applicable charges. For a service not managed as a
Render Blueprint, configure the same settings on that service:

- **Build command:** `pip install -r requirements.txt`
- **Start command:** `gunicorn --bind 0.0.0.0:$PORT app:app`
- **Persistent disk mount path:** `/var/data`
- **`TUSALAMA_DATABASE_PATH`:** `/var/data/tusalama.sqlite3`
- **`FLASK_SECRET_KEY`:** a persistent, private random value
- **`FLASK_COOKIE_SECURE`:** `1`

Set these values on Render before deploying. The app refuses to start on
Render if the session key or persistent database path is missing instead of
silently using an ephemeral database. For OpenAI analysis, also set
`OPENAI_API_KEY` and optionally `OPENAI_MODEL` (default: `gpt-4o-mini`). Keep
the key in Render's environment settings; never commit it.

Confirm the Render service deploys this repository's `main` branch and deploy
the latest commit. A `render.yaml` change does not update a manually configured
service until its settings are applied. Before switching database paths, use
the administrator database backup to preserve existing users and incidents;
an empty newly mounted disk will otherwise require account setup again. Keep
regular off-service backups as well.

## Forecasting and maps

Hotspot forecasts use explainable historical trends, not a trained machine
learning model or a crash-probability guarantee. Forecasts are withheld when
data is stale or insufficient. Recommendations are prompts for qualified road
safety professionals, not automatic instructions.

Interactive charts recalculate from current incident records and filters,
with an interactive 3D-style visual treatment whose depth represents fatal
incidents. The optional OpenAI feature reviews the existing evidence-qualified
historical forecast and sends only aggregated month, cause-category, and
hotspot counts; it does not send names, incident references, coordinates, or
raw report text. The numeric forecast remains an explainable historical trend,
not an independent AI model, verified accident causation, or an
exposure-adjusted prediction. No TomTom or ShareBarabara integration is
enabled.

Maps use Leaflet and OpenStreetMap. Location lookup uses the Nominatim service
and requires an internet connection. Google Maps integration is not currently
enabled.

## Tests

Install the dependencies as above, then run:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -v
```

## Project layout

```text
app.py                         Flask application and web routes
main.py                        Original menu-driven application
Models/                        Incident and road models
Services/                      Incident, risk, hotspot, forecast, and signal logic
Validation/                    Input validation
storage/                       CSV compatibility and SQLite persistence
templates/                     Dashboard, account, and report pages
static/                        Styles, scripts, and logo assets
tests/                         Web app and forecasting tests
incidents.csv                  Legacy CSV import source
requirements.txt               Web app dependencies
```

The original command-line application can be run with:

```powershell
.\.venv\Scripts\python.exe main.py
```

## Maintainer

Telvin Gachithi Kariithi

Improving road safety using technology and artificial intelligence.
