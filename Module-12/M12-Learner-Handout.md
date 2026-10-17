<!-- JHF-BRAND -->
<div align="center" style="padding:28px 20px; background:#ffffff; border:2px solid #e0e0e0; border-radius:12px;">
  <p style="margin:0 0 16px 0;">
    <img src="../assets/jhf-logo.png" alt="Jerusalem High-Tech Foundry (JHF)" height="54" style="vertical-align:middle; margin:0 22px;" />
    <img src="../assets/comcec-logo.png" alt="COMCEC - Cooperation for Development" height="72" style="vertical-align:middle; margin:0 22px;" />
  </p>
  <h1 style="color:#1a3c5e; margin:6px 0;">Agentic AI Bootcamp</h1>
  <h3 style="color:#0078d4; margin:4px 0; font-weight:600;">Module 12 &middot; Deploy a Memory Chat Agent to AWS &mdash; Learner Handout</h3>
  <hr style="border:0; border-top:1px solid #0078d4; width:60%; margin:16px auto;" />
  <p style="font-size:14px; color:#555; margin:6px 0;">
    <strong>Lead Trainer</strong><br/>
    <a href="https://www.linkedin.com/in/alaaldin-ahmed-260266150" target="_blank">Alaaldin Ahmed</a>
  </p>
  <p style="font-size:12.5px; color:#777; margin:8px 0 0 0;">
    Organized by <strong>Jerusalem High-Tech Foundry (JHF)</strong> &nbsp;&middot;&nbsp; In partnership with <strong>COMCEC</strong>
  </p>

# Module 12 — Deploy a Memory Chat Agent to AWS
## Learner Handout

> **Duration:** 3 hours · **Prereq:** M1–M11.
> **You need:** Python 3.12, Docker, an AWS account (Console access + AWS CLI), an OpenRouter key in `.env`.
> Today you **ship**: a streaming chat agent with short- and long-term memory, running on AWS behind HTTPS.

---

## Learning Objectives

After this module you can:

1. Explain **why** a chat agent uses **WebSockets** and **token streaming** instead of one big HTTP response.
2. Explain **short-term memory** (compaction) and **long-term memory** (vector store) and the cost of each.
3. Enforce a **budget**: message length cap, rate limit, bounded context.
4. **Containerize** an app and build the image **locally** (not on the server).
5. Deploy to **EC2 + CloudFront** and verify `wss://` streaming end to end.

---

## 1. The app

`starter-code/` is a complete general chat agent. No scenario: it just chats.

| File | Role |
|------|------|
| `app.py` | FastAPI: `/ws` (chat), `/health`, `/memory/stats`, serves the UI |
| `memory_manager.py` | Short-term compaction + long-term Chroma memory |
| `static/index.html` | Chat UI (shows **Compacting conversation...**) |
| `Dockerfile` | Image definition (embedding model baked in) |

## 2. Why WebSockets and streaming

An LLM answer takes seconds to finish. With plain HTTP the user stares at a blank screen until it is complete. With a **WebSocket** the connection stays open and the server pushes each token as the model produces it (`llm.astream`). The first words show in about a second, and the server can also push status events such as "compacting".

CloudFront supports WebSockets when caching is **disabled** and all headers are forwarded; an `https://` page then uses `wss://` automatically.

## 3. Memory and budget

**Short-term (the conversation window).** Every turn is added to the prompt, so cost grows. After **5 turns** the old messages are summarized by the LLM and only the **last 3** stay verbatim. The UI shows *Compacting conversation...* while this happens.

**Long-term (across sessions).** Durable facts the user states (for example "my name is Lea") are embedded and stored in Chroma. On each new message the top **3** similar memories (similarity ≥ 0.20) are recalled and added to the prompt. A new session therefore still knows you. Questions and pleasantries are *not* stored.

**Budget.** Messages are capped at 1000 characters, requests are rate limited per minute, and the context is bounded by compaction plus top-k recall. All limits are environment variables in `.env.example`.

## 4. Docker, built locally

Build the image on **your laptop**, then ship it. Building on a small server is slow and needs more memory.

```bash
docker buildx build --platform linux/amd64 -t chat-agent:latest --load .
docker save -o chat-agent-image.tar chat-agent:latest
```

`--platform linux/amd64` matters on Apple Silicon: EC2 runs x86.

## 5. AWS architecture

```
Browser --https/wss--> CloudFront --http:80--> EC2 (t3.micro, Docker) <-- image from S3
```

- **S3** holds the image tarball; EC2 downloads it through a presigned URL at boot.
- **EC2** security group allows port 80 **only from CloudFront** (managed prefix list), never from the world.
- **CloudFront** gives free HTTPS and `wss://`.

Follow **`AWS-DEPLOYMENT-GUIDE.html`** step by step (Console steps + CLI equivalents).

---

## Today's Lab

See `M12-Lab-Worksheet.md`: run locally → Docker → deploy → test memory, compaction and streaming → clean up.

## Deliverables

- [ ] Local run working, with compaction seen at turn 5
- [ ] Docker image built locally and run
- [ ] Public `https://….cloudfront.net` URL streaming a reply
- [ ] Proof of long-term memory in a **new** session
- [ ] AWS resources deleted

## Key Terms

| Term | Meaning |
|------|---------|
| WebSocket | Persistent two-way connection |
| Streaming | Sending tokens as they are generated |
| Compaction | Summarizing old turns to shrink context |
| Long-term memory | Facts stored in a vector DB across sessions |
| Presigned URL | Temporary signed link to a private S3 object |
| Prefix list | Managed set of IP ranges (CloudFront origin-facing) |

## Quiz

1. Why can't a normal request/response endpoint stream tokens as nicely?
2. What triggers compaction, and what is kept verbatim?
3. Why is `0.0.0.0/0` on port 80 avoided here?
4. Why build the image locally rather than on EC2?
5. A new session recalls your name. Which memory did that, and how?

---


<div align="center" style="padding:14px; border-top:2px solid #0078d4; margin-top:34px;">
  <p style="margin:0 0 8px 0;">
    <img src="../assets/jhf-logo.png" alt="JHF" height="28" style="vertical-align:middle; margin:0 14px; background:#ffffff; padding:6px 10px; border-radius:6px;" />
    <img src="../assets/comcec-logo.png" alt="COMCEC" height="40" style="vertical-align:middle; margin:0 14px; background:#ffffff; padding:6px 10px; border-radius:6px;" />
  </p>
  <p style="color:#888; font-size:13px; margin:0;">
    <strong>JHF Agentic AI Bootcamp</strong> &mdash; Module 12<br/>
    Lead Trainer: <a href="https://www.linkedin.com/in/alaaldin-ahmed-260266150">Alaaldin Ahmed</a><br/>
    Organized by Jerusalem High-Tech Foundry (JHF) &middot; In partnership with COMCEC
  </p>
</div>

