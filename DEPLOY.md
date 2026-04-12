# 📤 QUICK START: Push to GitHub + HuggingFace

## 5-Minute Setup

### For GitHub

```bash
# 1. Create repo on GitHub: https://github.com/new
#    Name: esig
#    Visibility: Public
#    Add MIT license

# 2. Copy your HTTPS URL from GitHub

# 3. Run these commands:
cd c:\Users\nathn\Desktop\vscode\esig_project\esig
git remote add origin https://github.com/YOUR_USERNAME/esig.git
git branch -M main
git push -u origin main
```

**Done!** Your code is now on GitHub at:
```
https://github.com/YOUR_USERNAME/esig
```

---

### For HuggingFace Spaces

```bash
# 1. Create Space on HF: https://huggingface.co/spaces
#    Name: esig
#    SDK: Docker
#    License: mit
#    Visibility: Public

# 2. Get your HF token: https://huggingface.co/settings/tokens

# 3. Run this command:
git remote add huggingface https://huggingface.co/spaces/YOUR_HF_USERNAME/esig
git push huggingface main

# When prompted for password, use your HF token
```

**Done!** Your API is live at:
```
https://USERNAME-esig.hf.space/
```

Interactive API docs:
```
https://USERNAME-esig.hf.space/docs
```

---

## What You Get

### GitHub
✅ Source code accessible worldwide
✅ Easy for evaluators to review code
✅ Version history and contributions
✅ Community discussion

### HuggingFace Space  
✅ **Live running API** (free hosting!)
✅ **Interactive API explorer** at `/docs`
✅ **Live demo** for evaluators to test
✅ **Example requests** right in the browser

---

## Sharing with Hackathon

Submit these links to the hackathon:

```
GITHUB:      https://github.com/YOUR_USERNAME/esig
HUGGINGFACE: https://huggingface.co/spaces/YOUR_USERNAME/esig
API DOCS:    https://USERNAME-esig.hf.space/docs
```

---

## Test Your Deployment

### Test GitHub (Code Review)
```
1. Visit: https://github.com/YOUR_USERNAME/esig
2. Browse code
3. Read ADVANCED_README.md
4. Check all files are there
```

### Test HuggingFace (Live API)
```
1. Visit: https://USERNAME-esig.hf.space/docs
2. Try "/health" endpoint
3. Try "/tasks" endpoint
4. Try "/threats/catalog" endpoint
5. Try "/reset" endpoint
```

---

## Troubleshooting

### Git Push Rejected
```
Error: failed to push some refs to repository

Solution:
git pull origin main --allow-unrelated-histories
git push -u origin main
```

### HF Deployment Stuck
- Wait 10 minutes (building Docker image)
- Check "App" tab for logs
- If failed, check requirements.txt

### API Not Responding
- Refresh the page
- Wait for "Running" status on HF
- Check space logs for errors

---

## Optional: Add OpenAI (For LLM Evaluation)

On HuggingFace Space:
1. Settings → Secrets
2. New secret:
   - Name: `OPENAI_API_KEY`
   - Value: `sk-...` (your OpenAI key)
3. Restart space

---

## What to Include in Submission

1. ✅ GitHub link (source code)
2. ✅ HuggingFace Space link (live demo)
3. ✅ Brief description:
   ```
   ESIG v2.0: Enterprise email training environment with:
   - 4 tasks (easy → expert)
   - 7 advanced threat types
   - GPT-4 reply evaluation
   - Gymnasium RL framework integration
   - SQLite multi-concurrent episodes (100+)
   - Comprehensive analytics
   ```

---

## Success Checklist

- [ ] Created GitHub repo
- [ ] Pushed code to GitHub
- [ ] GitHub links work (can view code)
- [ ] Created HF Space
- [ ] HF Space is "Running"
- [ ] API responds to `/health`
- [ ] API docs at `/docs` are accessible
- [ ] Can test endpoints in browser
- [ ] Links ready for submission

---

## Live Status Commands

```bash
# Check what remotes you have
git remote -v

# Push to both in one go (future commits)
git push origin main
git push huggingface main

# Or set up to push to both
git remote set-url origin --push https://github.com/YOUR_USERNAME/esig.git
git remote set-url --add origin https://huggingface.co/spaces/YOUR_USERNAME/esig
```

---

## Final Result

You now have:

```
┌──────────────────────────────────────────────────┐
│  Your ESIG Project is Live!                      │
├──────────────────────────────────────────────────┤
│ GitHub Code:     github.com/YOUR_USERNAME/esig   │
│ Live API:        USERNAME-esig.hf.space          │
│ API Explorer:    .../docs                        │
│ API Health:      .../health                      │
│ Threat Catalog:  .../threats/catalog             │
│ Analytics:       .../analytics/report            │
└──────────────────────────────────────────────────┘
```

✅ **Ready for hackathon evaluation!**

For detailed instructions:
- GitHub setup: See [PUSH_TO_GITHUB.md](PUSH_TO_GITHUB.md)
- HF setup: See [PUSH_TO_HUGGINGFACE.md](PUSH_TO_HUGGINGFACE.md)
