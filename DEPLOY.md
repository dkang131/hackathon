# Azure Deployment Guide for CafeMate

## Prerequisites

- Azure subscription ([free tier](https://azure.microsoft.com/free/) works)
- Azure CLI installed: https://docs.microsoft.com/cli/azure/install-azure-cli
- Your code pushed to GitHub (recommended)

---

## Step 1: Prepare Your Code

### 1.1 Environment Variables

Copy `.env.example` to `.env` for local testing:
```bash
cp .env.example .env
```

**Do NOT commit `.env` to git.** Azure will use Application Settings instead.

### 1.2 Required Files for Azure

Make sure these files exist in your repo:
- `pyproject.toml` — Python dependencies
- `requirements.txt` — Fallback for Azure's pip-based build
- `startup.sh` — Startup command for Linux App Service

They should already be there. If `requirements.txt` is missing:
```bash
uv pip freeze > requirements.txt
```

---

## Step 2: Create Azure Resources

### Option A: Azure Portal (GUI)

1. **Azure App Service**
   - Portal → Create a resource → Web App
   - Name: `cafemate-bot` (globally unique, becomes your URL)
   - Runtime: Python 3.13
   - Region: Southeast Asia (or closest to your users)
   - Plan: Free F1 (testing) or Basic B1 ($13/mo for production)

2. **Azure Blob Storage** (optional — for persistent menu/feedback data)
   - Portal → Create a resource → Storage account
   - Name: `cafematestorage` (lowercase, globally unique)
   - Performance: Standard
   - Create container: `menu-images` (for drink photos)

### Option B: Azure CLI (Faster)

Open PowerShell or Bash and run:

```bash
# Login
az login

# Create resource group
az group create --name rg-cafemate --location southeastasia

# Create App Service Plan (Free tier)
az appservice plan create \
  --name asp-cafemate \
  --resource-group rg-cafemate \
  --sku F1 \
  --is-linux

# Create Web App
az webapp create \
  --name cafemate-bot \
  --resource-group rg-cafemate \
  --plan asp-cafemate \
  --runtime "PYTHON:3.13"

# Create Storage Account (optional)
az storage account create \
  --name cafematestorage \
  --resource-group rg-cafemate \
  --location southeastasia \
  --sku Standard_LRS
```

Your app URL will be: `https://cafemate-bot.azurewebsites.net`

---

## Step 3: Configure Environment Variables in Azure

In Azure Portal:
1. Go to your Web App → **Settings** → **Configuration** → **Application settings**
2. Click **+ New application setting** for each:

| Setting Name | Example Value | Where to get it |
|---|---|---|
| `AZURE_OPENAI_ENDPOINT` | `https://your-resource.openai.azure.com/` | Azure OpenAI resource |
| `AZURE_OPENAI_API_KEY` | `your-key` | Azure OpenAI → Keys |
| `AZURE_OPENAI_DEPLOYMENT_NAME` | `gpt-4o` | Azure OpenAI → Deployments |
| `TELEGRAM_BOT_TOKEN` | `123456:ABC...` | @BotFather |
| `OWNER_TELEGRAM_ID` | `5832177797` | Message @userinfobot |
| `KITCHEN_GROUP_ID` | `-1003904000032` | Your kitchen group |
| `WEBHOOK_SECRET` | `random-secret-123` | Generate yourself |
| `WEBHOOK_URL` | `https://cafemate-bot.azurewebsites.net/webhook` | Your app URL + `/webhook` |

3. Click **Save** (this restarts the app)

**Security tip:** Never put secrets in code. Azure Application Settings are encrypted at rest.

---

## Step 4: Deploy the Code

### Option A: GitHub Deployment (Recommended)

1. Push your code to a GitHub repo
2. Azure Portal → Your Web App → **Deployment** → **Deployment Center**
3. Source: GitHub → Sign in → Select your repo/branch
4. Azure auto-builds and deploys on every push

### Option B: ZIP Deploy (Quick test)

```bash
cd d:\hackathon

# Create ZIP (exclude venv, git, data files)
7z a -r deploy.zip . -x!.venv -x!.git -x!__pycache__ -x!*.pyc

# Deploy
az webapp deployment source config-zip \
  --resource-group rg-cafemate \
  --name cafemate-bot \
  --src deploy.zip
```

### Option C: VS Code Extension

1. Install **Azure App Service** extension
2. Sign in to Azure
3. Right-click your app → **Deploy to Web App**

---

## Step 5: Configure Startup Command

Azure needs to know how to start your app:

1. Portal → Your Web App → **Settings** → **Configuration** → **General settings**
2. **Startup Command**: `bash startup.sh`
3. Click **Save**

The `startup.sh` script tries `uv` first, then falls back to `pip` + `uvicorn`.

---

## Step 6: Set Telegram Webhook

Once deployed, tell Telegram where to send updates:

```bash
# Replace with your actual values
BOT_TOKEN="your-bot-token"
WEBHOOK_URL="https://cafemate-bot.azurewebsites.net/webhook"
SECRET="your-webhook-secret"

curl "https://api.telegram.org/bot${BOT_TOKEN}/setWebhook?url=${WEBHOOK_URL}&secret_token=${SECRET}"
```

Verify:
```bash
curl "https://api.telegram.org/bot${BOT_TOKEN}/getWebhookInfo"
```

You should see `"url": "https://cafemate-bot.azurewebsites.net/webhook"` and `"has_custom_certificate": false`.

---

## Step 7: Test Your Deployed Bot

1. Open Telegram → message your bot: `/start`
2. Check logs: Azure Portal → Your Web App → **Monitoring** → **Log stream**
3. Health check: `curl https://cafemate-bot.azurewebsites.net/health`

---

## Important: Data Persistence

**Azure App Service's local filesystem is NOT persistent.** When the app restarts (happens daily on Free tier), files in `data/menu.json` and `data/feedback.json` will be lost.

### Solutions:

**Option A: Use Azure Blob Storage (Recommended for production)**
- Store `menu.json` and `feedback.json` in Blob Storage
- Modify `menu_manager.py` and `feedback_manager.py` to read/write from Blob

**Option B: Mount Azure Files (Simplest)**
- Portal → Your Web App → **Settings** → **Configuration** → **Path mappings**
- Mount an Azure File Share to `/home/data`
- Update your code to use `/home/data/` instead of `./data/`

**Option C: Reload menu after each restart**
- Use `/admin_reload` command after deployments
- Accept that feedback history resets (not ideal)

---

## Troubleshooting

| Problem | Solution |
|---|---|
| `ModuleNotFoundError` | Azure reads `pyproject.toml` or `requirements.txt`. Make sure both are committed. |
| App won't start | Check **Log stream** for errors. Verify startup command is `bash startup.sh`. |
| Telegram not receiving | Verify webhook URL is correct and HTTPS. Check `getWebhookInfo`. |
| 401/403 errors | Check `OWNER_TELEGRAM_ID` and `WEBHOOK_SECRET` match between code and Azure settings. |
| Build fails | If `uv` isn't available, Azure falls back to `pip`. Check `requirements.txt` is present. |
| Data lost after restart | See **Data Persistence** section above. Use Azure Files or Blob Storage. |

---

## Estimated Costs

| Service | Free Tier | Basic Tier |
|---|---|---|
| App Service (F1) | Free | — |
| App Service (B1) | — | ~$13/month |
| Azure OpenAI | Pay-per-use | Pay-per-use |
| Blob Storage | 5GB free | ~$0.02/GB/month |
| Azure Files | — | ~$0.06/GB/month |

**Total for production:** ~$15-30/month depending on usage.

---

## Quick Reference

```bash
# View logs
az webapp log tail --name cafemate-bot --resource-group rg-cafemate

# Restart app
az webapp restart --name cafemate-bot --resource-group rg-cafemate

# Update a single app setting
az webapp config appsettings set \
  --name cafemate-bot \
  --resource-group rg-cafemate \
  --settings KEY=value
```