<!-- JHF-BRAND -->
<div align="center" style="padding:28px 20px; background:#ffffff; border:2px solid #e0e0e0; border-radius:12px;">
  <p style="margin:0 0 16px 0;">
    <img src="../assets/jhf-logo.png" alt="Jerusalem High-Tech Foundry (JHF)" height="54" style="vertical-align:middle; margin:0 22px;" />
    <img src="../assets/comcec-logo.png" alt="COMCEC - Cooperation for Development" height="72" style="vertical-align:middle; margin:0 22px;" />
  </p>
  <h1 style="color:#1a3c5e; margin:6px 0;">Agentic AI Bootcamp</h1>
  <h3 style="color:#0078d4; margin:4px 0; font-weight:600;">Module 12 &middot; Lab Worksheet &mdash; Deploy a Memory Chat Agent</h3>
  <hr style="border:0; border-top:1px solid #0078d4; width:60%; margin:16px auto;" />
  <p style="font-size:14px; color:#555; margin:6px 0;">
    <strong>Lead Trainer</strong><br/>
    <a href="https://www.linkedin.com/in/alaaldin-ahmed-260266150" target="_blank">Alaaldin Ahmed</a>
  </p>
  <p style="font-size:12.5px; color:#777; margin:8px 0 0 0;">
    Organized by <strong>Jerusalem High-Tech Foundry (JHF)</strong> &nbsp;&middot;&nbsp; In partnership with <strong>COMCEC</strong>
  </p>

# Module 12 — Lab Worksheet
## Deploy a Memory Chat Agent to AWS

> **Time:** ~2.5 hours · Your instructor demos each phase first, then you repeat it.
> **Cost:** a t3.micro + CloudFront for a few hours is pennies. **Delete everything at the end.**

---

## Part 1 — Run locally (20 min)

```bash
cd starter-code
python3.12 -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env        # Windows: copy .env.example .env  -> then put your OpenRouter key in .env
uvicorn app:app --port 8000
```

Open http://localhost:8000.

- [ ] Reply streams word by word
- [ ] After 5 turns the UI shows **Compacting conversation...**
- [ ] Say "My name is <you> and I love tea." Reload the page (new session) and ask "What do you know about me?" — it remembers.
- [ ] `http://localhost:8000/memory/stats` shows counts

## Part 2 — Docker (20 min)

```bash
docker buildx build --platform linux/amd64 -t chat-agent:latest --load .
docker run --rm -p 8000:8000 --env-file .env chat-agent:latest
curl http://localhost:8000/health
docker save -o chat-agent-image.tar chat-agent:latest
```

- [ ] Health returns OK, chat works from the container

## Part 3 — Deploy to AWS (60 min)

Follow `AWS-DEPLOYMENT-GUIDE.html` (use region **eu-west-1** or your instructor's region):

1. S3 bucket → upload `chat-agent-image.tar` → create a presigned URL
2. Security group: port 80 from the CloudFront prefix list only
3. EC2 t3.micro (Ubuntu 22.04) with the user-data script from the guide
4. Elastic IP → copy its **Public IPv4 DNS**
5. CloudFront: origin = that DNS, HTTP only port 80, caching **disabled**, forward all viewer headers, allow all methods

- [ ] `https://<id>.cloudfront.net/health` returns OK
- [ ] Chat streams and compaction appears on the public URL

## Part 4 — Prove it (15 min)

- [ ] Tell the agent a fact, open the URL in a private window, ask about it
- [ ] Write 3 sentences: what would change at 1000 users? (hint: Chroma is local to one instance)

## Stretch

- Lower `SUMMARIZE_AFTER_TURNS` to 3 and observe
- Add a system persona via the prompt
- Put `OPENROUTER_API_KEY` in AWS Secrets Manager instead of user-data

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| Page loads, chat never answers | Wrong or missing API key in `.env` / user-data |
| `exec format error` on EC2 | Image built for arm64; rebuild with `--platform linux/amd64` |
| CloudFront 502/504 | Wait ~2 min after launch; check SG uses the CloudFront prefix list |
| Origin rejected by CloudFront | Use the Public IPv4 **DNS name**, not the IP |
| Chat disconnects | Caching must be disabled and origin read timeout 60s |
| No logs | Use EC2 → Actions → Monitor → **Get system log** |

## Submit

Your CloudFront URL, a screenshot of *Compacting conversation...*, a screenshot of cross-session memory, and confirmation that resources were deleted.

## Cleanup checklist

- [ ] CloudFront distribution disabled → deleted
- [ ] EC2 terminated, Elastic IP **released**
- [ ] Security group deleted
- [ ] S3 bucket emptied and deleted

---


---

<div align="center" style="padding:14px; border-top:2px solid #0078d4; margin-top:34px;">
  <p style="margin:0 0 8px 0;">
    <img src="../assets/jhf-logo.png" alt="JHF" height="28" style="vertical-align:middle; margin:0 14px; background:#ffffff; padding:6px 10px; border-radius:6px;" />
    <img src="../assets/comcec-logo.png" alt="COMCEC" height="40" style="vertical-align:middle; margin:0 14px; background:#ffffff; padding:6px 10px; border-radius:6px;" />
  </p>
  <p style="color:#888; font-size:13px; margin:0;">
    <strong>JHF Agentic AI Bootcamp</strong> &mdash; Module 12 Lab<br/>
    Lead Trainer: <a href="https://www.linkedin.com/in/alaaldin-ahmed-260266150">Alaaldin Ahmed</a><br/>
    Organized by Jerusalem High-Tech Foundry (JHF) &middot; In partnership with COMCEC
  </p>
</div>

