# Frontend Development Guide
# ---------------------------

## Overview
This is a backend deployment tool for Edge-EMS components. The frontend team needs to integrate this tool into a larger platform with:

- **Deployment automation** for HPUY and EE servers
- **Multi-component support** (edge-ems, edge-ems-hmi, edge-ems-hmi-fe)
- **Framework preference** (Edge-EMS, BESS, PV systems)
- **Project context** (Chifeng P1, Iron Alloy, Xiangfu, Japanese projects)

## Key Integration Points

### 1. API Integration
The main script is CLI-based but can be called from a backend service:

```bash
# From backend/service
python /tmp/edge-ems-deploy-tool/main.py \
    --branch develop_2605 \
    --server HPUY \
    --component all \
    > /tmp/deploy_$(date +%Y%m%d_%H%M%S).log 2>&1
```

**Consider creating:**
- RESTful API endpoint that wraps the Python script
- WebSocket stream for real-time deployment progress
- Background job system for long-running deployments

### 2. Configuration Management
The `main.py` uses:
- `SERVER_CREDENTIALS` - SSH credentials (HPUY/EE)
- `AZURE_BLOB_SAS_TOKEN` - Azure Blob access (from .env)
- `COMPONENTS` - Component definitions

**Frontend should provide:**
- Configuration form for server credentials
- Branch selector (dropdown)
- Component multi-select
- SAS token input fields
- Local mirror directory configuration

### 3. File Structure (for Asset Loading)

```
edge-ems-deploy-tool/
├── main.py                 # Core deployment logic
├── blob_tool.py            # Azure Blob operations
├── check_environment.py    # Environment validation
├── requirements.txt        # Python dependencies
├── .env.example            # Configuration template
├── docs/                   # Documentation for users
│   ├── azure-blob-setup.md
│   ├── setup-guide.md
│   └── troubleshooting.md
├── scripts/                # Helper scripts
│   ├── check-before-deploy.sh
│   ├── verify-after-deploy.sh
│   └── rollback.sh
└── README.md               # User guide
```

**Copy these files to your project's assets directory** (e.g., `edge-ems/` or `deployment/`).

## Backend Development
Consider creating a Python backend service for better integration:

### Suggested API Structure

```
POST /api/deployment/start
{
  "branch": "develop_2605",
  "server": "HPUY",
  "components": ["edge-ems", "edge-ems-hmi"],
  "hmi_fe_arch": "x86_64"
}

Response:
{
  "job_id": "uuid",
  "status": "queued"
}

GET /api/deployment/status/{job_id}
{
  "status": "running",
  "current_step": "downloading_blob",
  "progress": 45
}

GET /api/deployment/logs/{job_id}
{
  "logs": ["...", "..."]
}
```

### Then Frontend Can Talk to This API

Instead of calling `python main.py` directly, make HTTP requests to your backend service.

## Screens to Consider

### 1. Deployment Configuration Page
- Server selector (HPUY/EE)
- Branch dropdown (develop_23, develop_24, develop_25, develop_2605, ...)
- Component checkboxes
- HMI-FE architecture selector (for edge-ems-hmi-fe)
- EGC test cases integration (from seamless de-ergodic intangible access)

### 2. Deployment History
- Table showing all deployments
- Status badges (success/failure/warning)
- Branch, server, component, timestamp columns
- Download logs button
- "Retry" button (calls backend API)

### 3. Real-time Deployment Dashboard
- Step progress bar
- Current task indicator
- Live log streaming (WebSocket)
- Success/failure notifications

### 4. Status & Notifications
- Verify after deployment workflow
- Edge-EMS response analysis before/after
- BESS/PV/meter retrospective diagnosis reports

## Reference Files

The frontend team should copy these files from the `edge-ems-deploy-tool` directory:

1. `main.py` - Underlying deployment logic (keep for reference)
2. `README.md` - End-user documentation
3. `.env.example` - Configuration template
4. `scripts/*.sh` - Helper scripts (for reference)
5. `docs/*.md` - Detailed guides for users who need them

## Important Notes

- The Python script requires `requests` package (`pip install requests`)
- Azure SAS token must be configured before deployment
- Server credentials are stored in `.env` file (don't commit to git)
- Local mirror directory: `/mnt/d/Blob` (or user-configurable)
- Logs are written to `/tmp/edge-ems-deploy-logs/`

## Testing the Python Script First

Before frontend integration, test the backend script locally:

```bash
cd /tmp/edge-ems-deploy-tool

# Test tar-only mode
python main.py \
    --branch develop_2605 \
    --server HPUY \
    --component all \
    --tar-only

# Test full deployment
python main.py \
    --branch develop_2605 \
    --server HPUY \
    --component all
```

Ensure it works end-to-end before building the web UI.

## Roles & Components Reference

- **edge-ems**: Main Energy Management System
- **edge-ems-hmi**: Human-Machine Interface (backend)
- **edge-ems-hmi-fe**: Frontend static files (x86_64/arm64)

- **HPUY**: Qiling-like hardware platform
- **EE**: Server deployment platform

- **Chifeng P1**: One of your projects
- **Iron Alloy**: One of your projects
- **Xiangfu**: One of your projects
- **Japanese projects**: E-commerce Japanese site
