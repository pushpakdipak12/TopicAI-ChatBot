# TopicChat AI — one agent, multiple selectable topics

A working beginner-friendly single-agent chatbot project. Select a topic (General, Python, DevOps, AWS, Agentic AI, etc.), ask questions, and keep follow-up context separately per topic.

## Architecture

Browser (built-in HTML UI) -> FastAPI POST /chat -> one LangChain `create_agent` (LangGraph) -> Groq GPT-OSS 20B -> optional calculator tool -> answer

- One shared agent handles every topic; a `dynamic_prompt` changes its specialty for each request.
- Each `(session_id, topic)` pair uses its own LangGraph `thread_id` in `InMemorySaver`.
- The UI remembers message bubbles for the browser tab using `sessionStorage`.
- No database, vector store, hardcoded question/answer database, or separate frontend server.
- The model uses its pretrained knowledge; it does NOT have live web search.

## Run locally (Python 3.12, PowerShell)

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
Copy-Item .env.example .env
```

Open `.env`, insert your **real** GROQ_API_KEY from https://console.groq.com/keys.
Do not share it, push it to GitHub, or embed it in the browser.

```powershell
python -m pytest -q
python -m uvicorn app.main:app --reload
```

Open **http://127.0.0.1:8000** to chat, or **http://127.0.0.1:8000/docs** to test endpoints.

## API

POST `/chat` with JSON:

```json
{
  "session_id": "d48c3b64-7ccd-424c-a55b-53b4a2c9b753",
  "topic": "Python",
  "message": "What is a list?"
}
```

Re-use the same session_id and topic to continue a chat. Change topic for separate history.
Use the **New chat** button in the UI for a fresh conversation in the current topic.

## Docker

```powershell
docker build -t topicchat:local .
docker run --rm --env-file .env -p 8000:8000 topicchat:local
```

Then browse http://127.0.0.1:8000.

## GitHub Actions

`.github/workflows/ci.yml` runs pytest and builds a Docker image for main branch pushes and PRs. AWS deploy is **not** enabled yet; the next project phase is ECR + GitHub OIDC + ECS Fargate.

## Important limits before AWS public deployment

- In-memory message history disappears after restarts; each ECS task would have independent history. For production, use a database-backed LangGraph checkpointer (e.g. PostgreSQL), or sticky routing if appropriate.
- No public-user authentication, rate limiting or usage quotas yet. **Do not expose publicly until these are added**, otherwise strangers can consume your Groq API quota.
- GitHub Actions tests mock model calls, so they don't prove a live Groq response succeeds. Test locally with a real key.
- This project does not have retrieval or live internet search. It will not automatically know today's news or current prices.
- Only one Uvicorn worker is used so in-memory session history is consistent for local learning.

## ChatGPT-style answer formatting

Answers use Markdown as the model output format, but the **UI renders it to HTML**.
The server renders headings, emphasis, code fences, lists, and tables using
`mistune` with raw HTML escaping and unsafe URL protocols disabled. Remote
images are never loaded automatically. The browser styles rendered answers,
adds horizontal scrolling to wide tables, and adds a Copy code button.

- The API returns both `answer` (raw text, for programmatic callers) and
  `answer_html` (safe rendered HTML for the bundled web UI).
- Only the server-produced `answer_html` is inserted as HTML. User messages
  and error messages remain plain text.
- Previously saved conversations in this browser tab might still show their
  original raw Markdown. Click **New chat** for newly formatted answers.

## AWS deployment (new)

See [AWS_DEPLOYMENT.md](AWS_DEPLOYMENT.md) for a staged ECS Fargate / ECR / GitHub OIDC deployment tutorial. The manual deployment workflow is `.github/workflows/deploy-aws.yml`.
