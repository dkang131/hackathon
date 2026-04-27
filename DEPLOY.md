# Azure Deployment Guide for CafeMate

## Prerequisites

- Azure subscription (free tier works)
- Azure CLI installed: https://docs.microsoft.com/cli/azure/install-azure-cli
- Your code pushed to GitHub (recommended) or local Git

---

## Step 1: Create Resources (One-time)

### Option A: Azure Portal (GUI)

1. **Azure App Service**
   - Portal → Create a resource → Web App
   - Name: `cafemate-bot` (globally unique)
   - Runtime: Python 3.13
   - Region: Southeast Asia
   - Plan: Free F1 (testing) or Basic B1 ($13/mo)

2. **Azure Blob Storage** (optional, for menu images)
   - Portal → Create a resource → Storage account
   - Name: `cafematestorage` (lowercase, unique)
   - Performance: Standard
   - Create container: `menu-images`

### Option B: Azure CLI (Faster)

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

---

## Step 2: Configure Environment Variables

In Azure Portal:
1. Go to your Web App → **Settings** → **Configuration** → **Application settings**
2. Click **+ New application setting** for each:

| Setting Name | Value | Source |
|---|---|---|
| `AZURE_OPENAI_ENDPOINT` | `https://your-resource.openai.azure.com/` | Azure OpenAI |
| `AZURE_OPENAI_API_KEY` | `your-key` | Azure OpenAI |
| `AZURE_OPENAI_DEPLOYMENT_NAME` | `your-deployment` | Azure OpenAI |
| `TELEGRAM_BOT_TOKEN` | `your-bot-token` | @BotFather |
| `OWNER_TELEGRAM_ID` | `5832177797` | @userinfobot |
| `KITCHEN_GROUP_ID` | `-1234567890` | Your kitchen group |
| `WEBHOOK_SECRET` | `random-secret-string` | Generate yourself |
| `WEBHOOK_URL` | `https://cafemate-bot.azurewebsites.net/webhook` | Your app URL |

3. Click **Save** (this restarts the app)

**Security tip:** For production, use Azure Key Vault instead of plain app settings.

---

## Step 3: Deploy the Code

### Option A: Deploy from GitHub (Recommended)

1. Push your code to GitHub
2. Azure Portal → Your Web App → **Deployment** → **Deployment Center**
3. Source: GitHub
4. Sign in and select your repo/branch
5. Azure auto-builds and deploys on every push

### Option B: Deploy with Azure CLI + ZIP

```bash
# From your project directory
cd d:\hackathon

# Create ZIP (exclude .venv, .git, etc.)
7z a -r deploy.zip . -x!.venv -x!.git -x!data\*.png -x!__pycache__

# Deploy
az webapp deployment source config-zip \
  --resource-group rg-cafemate \
  --name cafemate-bot \
  --src deploy.zip
```

### Option C: VS Code Extension

1. Install **Azure App Service** extension in VS Code
2. Sign in to Azure
3. Right-click your app → **Deploy to Web App**

---

## Step 4: Configure Startup Command

Azure needs to know how to start your FastAPI app:

1. Portal → Your Web App → **Settings** → **Configuration** → **General settings**
2. **Startup Command**: `uv run uvicorn main:app --host 0.0.0.0 --port 8000`
3. Click **Save**

**Note:** If `uv` is not available in Azure's build, use this instead:
```
python -m pip install -r requirements.txt && uvicorn main:app --host 0.0.0.0 --port 8000
```

---

## Step 5: Set Telegram Webhook

Once deployed, tell Telegram where to send updates:

```bash
# Replace with your actual bot token and Azure URL
curl "https://api.telegram.org/bot<TOKEN>/setWebhook?url=https://cafemate-bot.azurewebsites.net/webhook&secret_token=your-webhook-secret"
```

Verify webhook is set:
```bash
curl "https://api.telegram.org/bot<TOKEN>/getWebhookInfo"
```

---

## Step 6: Test Your Deployed Bot

1. Open Telegram and message your bot: `/start`
2. Check logs: Azure Portal → Your Web App → **Monitoring** → **Log stream**
3. Health check: `curl https://cafemate-bot.azurewebsites.net/health`

---

## Troubleshooting

| Problem | Solution |
|---|---|
| `ModuleNotFoundError` | Make sure `pyproject.toml` is deployed; Azure reads it |
| App won't start | Check startup command in Configuration > General settings |
| Telegram not receiving | Verify webhook URL is correct and HTTPS |
| 403 Forbidden | Check `OWNER_TELEGRAM_ID` and `WEBHOOK_SECRET` match |
| Build fails | Azure may not support `uv` — switch to `pip` + `requirements.txt` |

---

## Switching from `uv` to `pip` for Azure

If Azure's build doesn't support `uv`, create a `requirements.txt`:

```bash
uv pip freeze > requirements.txt
```

And update startup command to:
```
pip install -r requirements.txt && uvicorn main:app --host 0.0.0.0 --port 8000
```

---

## Estimated Costs

| Service | Free Tier | Basic Tier |
|---|---|---|
| App Service (F1) | Free | — |
| App Service (B1) | — | ~$13/month |
| Azure OpenAI | Pay-per-use | Pay-per-use |
| Blob Storage | 5GB free | ~$0.02/GB/month |

**Total for production:** ~$15-30/month depending on usage.
