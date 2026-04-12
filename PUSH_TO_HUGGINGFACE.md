# 🤗 Deploy ESIG to HuggingFace Spaces

## Overview

HuggingFace Spaces gives you a free environment to run your FastAPI server online. Perfect for demos and evaluation!

---

## Step-by-Step Setup

### 1. Create HuggingFace Account

1. Go to [huggingface.co](https://huggingface.co)
2. Sign up (free account)
3. Create Personal Access Token:
   - Settings → Access Tokens → New Token
   - Copy the token (keep it secret!)

### 2. Create a New Space

1. Go to [huggingface.co/spaces](https://huggingface.co/spaces)
2. Click "Create new Space"
3. Fill in details:
   ```
   Space name: esig
   License: mit
   Visibility: Public
   Space SDK: Docker
   ```
4. Click "Create Space"

### 3. Enable Git on Your Local Machine

```bash
cd c:\Users\nathn\Desktop\vscode\esig_project\esig

# Configure git with HF credentials
git config --global user.email "your_email@example.com"
git config --global user.name "Your Name"
```

### 4. Add HuggingFace Remote and Push

```bash
# Add HF remote (replace USERNAME with your HF username)
git remote add huggingface https://huggingface.co/spaces/USERNAME/esig

# Push to HuggingFace
git push huggingface main

# When prompted for password, use your HuggingFace token as password
# (some systems may ask for Personal Access Token)
```

### 5. Monitor Deployment

1. Go to your Space URL: `https://huggingface.co/spaces/USERNAME/esig`
2. Watch the "App" tab for build logs
3. Wait for deployment to complete (5-10 minutes)
4. Access your live API when ready! 🎉

---

## Use HuggingFace Secrets (For OpenAI API)

To use GPT-4 evaluation in production:

1. On Space page → Settings → Secrets
2. Add new secret:
   ```
   Name: OPENAI_API_KEY
   Value: sk-...
   ```

The server will automatically use this API key.

---

## Space Files Setup

Your Dockerfile already handles everything! The repo structure is:

```
README.md              ← Shows on Space homepage
Dockerfile            ← Builds the container
requirements.txt      ← Installs dependencies
server/main.py        ← FastAPI app
```

HuggingFace will automatically:
- Build Docker image
- Install requirements
- Start FastAPI server on port 7860

---

## Access Your Live API

After deployment, your API is at:
```
https://USERNAME-esig.hf.space/
```

### Try these endpoints:

```bash
# Health check
curl https://USERNAME-esig.hf.space/health

# API docs (interactive)
https://USERNAME-esig.hf.space/docs

# List tasks
curl https://USERNAME-esig.hf.space/tasks

# Get threat catalog
curl https://USERNAME-esig.hf.space/threats/catalog
```

### Interactive API Explorer

Your full API documentation is at:
```
https://USERNAME-esig.hf.space/docs
```

You can test all endpoints directly in the browser! 🎯

---

## Sharing Your Space

Once live, share these links:

1. **Space URL**: `https://huggingface.co/spaces/USERNAME/esig`
   - Shows on HF profile
   - Easy share link

2. **API Endpoint**: `https://USERNAME-esig.hf.space/`
   - For evaluators
   - Direct access

3. **API Docs**: `https://USERNAME-esig.hf.space/docs`
   - Interactive Swagger UI
   - Test endpoints easily

---

## Complete Setup Commands (Copy & Paste)

```bash
cd c:\Users\nathn\Desktop\vscode\esig_project\esig

# If not already added
git remote add huggingface https://huggingface.co/spaces/YOUR_HF_USERNAME/esig

# Push to HuggingFace
git push huggingface main

# When prompted for password:
# - Use token type: Personal Access Token
# - Or paste your HF API token as password
```

---

## Troubleshooting

### Build fails?
- Check logs in HF Space settings
- Usually missing dependency → fix requirements.txt

### Endpoint not accessible?
- Wait 5-10 min for deployment
- Check Space status (should show "Running")
- Refresh page

### API is slow?
- HF free tier is slower than paid
- For better performance, use paid SpaceRunner tier

### Need GPT-4 evaluation?
- Add OPENAI_API_KEY to Space Secrets
- Automatic on next deploy

---

## Live Demo Example

Your API will work like this:

```bash
# From anywhere in the world
curl -X POST "https://YOUR_SPACE/reset?task_id=task1_easy"
curl -X POST "https://YOUR_SPACE/step" \
  -H "Content-Type: application/json" \
  -d '{"action_type": "triage_lock", "params": {"email_id": "EMAIL-001"}}'
```

---

## Monitoring

On the Space page:
- **App tab**: Live logs of your server
- **Settings**: Configure secrets, visibility, resources
- **Community**: Discussion section for feedback
- **Files**: Browse uploaded files

---

## Space Badges (Optional)

Add to your GitHub README:

```markdown
[![HuggingFace Space](https://img.shields.io/badge/🤗-Open%20in%20Spaces-blue.svg)](https://huggingface.co/spaces/YOUR_USERNAME/esig)
```

---

## Comparison: GitHub vs HuggingFace Spaces

| Feature | GitHub | HF Space |
|---------|--------|----------|
| **Code Storage** | ✅ Yes | ✅ Yes |
| **Live API** | ❌ No | ✅ Yes (free) |
| **Interactive Docs** | ❌ No | ✅ Yes |
| **Easy Share** | ✅ Yes | ✅ Yes |
| **Evaluation Host** | Manual | Automatic |

**Recommendation**: Use **GitHub for code** + **HF Space for live demo**

---

## Next Steps

1. ✅ Push code to GitHub
2. ✅ Deploy to HuggingFace Space
3. ✅ Copy Space URL
4. ✅ Test endpoints at `/docs`
5. ✅ Share with hackathon evaluators

## Final URLs to Share

Once deployed, you have:
- **GitHub**: `https://github.com/YOUR_USERNAME/esig` (source code)
- **HF Space**: `https://huggingface.co/spaces/YOUR_USERNAME/esig` (live demo)
- **API Docs**: `https://YOUR_USERNAME-esig.hf.space/docs` (interactive)

✅ **Done! Your project is now live and accessible!**
