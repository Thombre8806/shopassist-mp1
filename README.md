# ShopAssist — Mini-Project 1


Order support for Northwind Store (a fictional online store): a FastAPI service with per-session memory, three
validated tools, a defended system prompt and streamed answers. The model is reached only through a LiteLLM
gateway, and both run together with Docker Compose.

**Author:**  OM THOMBRE, Thombre8806

**Model tested:** shopassist → groq/openai/gpt-oss-20b (primary), with groq/openai/gpt-oss-120b as the backup model.

## Architecture

```
browser / client ──► app (FastAPI, :8000) ──► litellm gateway (:4000) ──► Groq
                     memory · prompt · tools    master key · fallback · cost      API_KEY lives only here
```

## API

| Method | Path | What it does |
|---|---|---|
| GET | `/health` | Liveness, plus the running model, gateway, memory strategy and tools |
| POST | `/chat` | `{"session_id", "message"}` → `{"answer", "tool_steps", "turns"}` |
| POST | `/chat/stream` | The same, streamed as Server-Sent Events: `tool`, `token`…, `done` |
| DELETE | `/sessions/{id}` | Forget one conversation |

## Run with Docker Compose (Path A)

```powershell
docker compose up --build       
```
Then open http://localhost:8000/docs. You should see the FastAPI Swagger documentation, where you can test the chat endpoints and check whether ShopAssist returns answers and tool results correctly.



## Run without Docker (Path B)

```powershell
uv sync

uv run --with "litellm[proxy]==1.80.0" litellm --config gateway/config.yaml --port 4000

uv run uvicorn app.main:app --port 8000
```

## Evidence

```powershell
uv run python eval/run_eval.py      
```
Needs the gateway running; writes experiments/mp1_results.md.


## Summary

golden: 10/10

golden_right_tools: 10/10

memory: pass

attacks_resisted: 3/4


## Design

ShopAssist uses a sliding-window memory strategy with KEEP_TURNS = 4 to control context size and reduce token usage while retaining recent conversation history. It has three tools: get_order_status checks order information, get_delivery_estimate checks delivery details, and check_return_eligibility applies the store's return rules. Tool arguments are validated, and invalid arguments raise a ValueError that is returned to the model as an INVALID message instead of crashing the application. The system prompt contains security rules that prevent users from overriding system instructions, revealing secrets or performing unauthorized actions, but the smuggle attack showed that prompt-based security is not perfect. LiteLLM provides centralized model routing, API key management, cost tracking and automatic fallback from the primary model to the backup model. The biggest production limitation is that session memory is stored in RAM, so restarting the application can lose conversations; Redis and authenticated session IDs would help make it more reliable.