# API Dependency Planner

> Given a plain-English goal — *"merge a pull request"* or *"reply to an email thread"* —
> automatically discover the exact sequence of API calls required, annotated with what you provide
> and what each step produces.

---

## The Problem

Modern SaaS platforms expose hundreds of API endpoints. Using them correctly is non-trivial:

| Challenge | Reality |
|---|---|
| APIs have strict call-ordering requirements | You cannot merge a PR without first fetching it |
| Outputs of one call must feed inputs of the next | `repo_id` from GET flows into CREATE_ISSUE |
| Documentation is vast and scattered | GitHub alone has 600+ endpoints |
| Developers waste hours tracing dependencies manually | Especially painful for cross-service workflows |

**API Dependency Planner solves this.** Describe what you want to do in plain English, and the system maps the full dependency chain — which tools to call, in what order, with what data flowing between them.

---

## What It Does

- **Two platforms supported** — GitHub (issues, PRs, merges) and Google Workspace (Gmail, Calendar, Drive, Sheets)
- **Hybrid planning engine** — data-driven BFS graph first, LLM ranking second
- **Field-level dependency tracking** — knows exactly which field from step N feeds into step N+1
- **User input annotation** — tells you upfront what *you* need to provide vs what the API chain produces automatically
- **Interactive dependency graph** — visual left-to-right flow with color-coded edges

---

## Architecture

```
User Query (plain English)
         │
         ▼
┌─────────────────────┐
│   Keyword Filter    │  Narrows 500+ tools → ~20 relevant candidates
│   (tools.py)        │  using intent maps + slug/field scoring
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│   BFS Dependency    │  Builds a directed graph on the filtered subset.
│   Graph Builder     │  Matches produces_candidates → inputs by field name.
│   (dependency.py)   │  Returns up to 5 valid chains.
└────────┬────────────┘
         │
         ├──── chains found? ──── YES ──▶ rank_plan()   LLM picks the best chain
         │                                               from BFS candidates
         └──── chains found? ──── NO  ──▶ llm_plan()    LLM builds chain from
                                                         scratch using tool catalog
         │
         ▼
┌─────────────────────┐
│   Chain Validator   │  Drops hallucinated slugs.
│   + Analyzer        │  Classifies each input as: user-provided vs chained.
│   (tools.py)        │
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│   Graphviz Render   │  Left-to-right dependency graph.
│   (graph.py)        │  Green dashed = user input. Amber solid = chained data.
└─────────────────────┘
```

---

## Planning Engine — BFS + LLM Hybrid

This is the core of the system. Two strategies work together:

### Stage 1 — Data-Driven BFS (`dependency.py`)

Builds a directed graph purely from field-name matching across tool definitions:

```
Tool A  produces_candidates: "repo_id, full_name"
Tool B  inputs:              "repo_id, title, body"
                                  ↑
                             match → draw edge A → B
```

**Match scoring:**

| Match type | Score | Example |
|---|---|---|
| Input ends with `_<output>` | 3 (strong) | output=`id`, input=`issue_id` |
| Exact field name match | 2 | output=`repo_name`, input=`repo_name` |
| Output is `id`, input ends `_id` | 1 (weak) | generic id propagation |

**Domain filtering** — tools are grouped by domain (ISSUE, PULL, GMAIL, CALENDAR…). Edges are only drawn within the same domain by default, preventing nonsensical chains like `LIST_COMMITS → CREATE_ISSUE`. The filter relaxes automatically for cross-service goals (e.g. Calendar → Gmail for "daily agenda email").

BFS explores the graph from the most-connected nodes and returns up to 5 valid chains.

### Stage 2 — LLM Ranking or Fallback (`planner.py`)

**If BFS found chains →** `rank_plan()` sends all candidates to `llama-3.3-70b-versatile` (Groq) and asks it to pick the best one for the user's goal. The LLM is only choosing, not inventing — much more reliable.

**If BFS found nothing →** `llm_plan()` sends the filtered tool catalog directly and asks the LLM to construct the chain from scratch, using strict rules about field satisfaction and fetch-before-act ordering.

---

## Tool Filtering (`tools.py`)

Before BFS runs, the tool catalogue is narrowed from 500+ to ~20 using a two-pass filter:

**Pass 1 — Intent matching**
The user query is compared against a curated intent map:
```python
"merge pr": ["pull", "merge", "repo", "get"]
"reply to email": ["reply", "message", "thread", "email", "gmail", "fetch"]
```
The best-matching intent's keywords are used to score tools.

**Pass 2 — Slug + field scoring**
```
score += 3  if keyword in tool slug
score += 1  if keyword in tool inputs
score += 1  if keyword in tool produces_candidates
```

Tools that introduce create/delete/send actions are suppressed unless the user's query explicitly contains those verbs — preventing `CREATE_REPOSITORY` from appearing in a "create issue" chain.

---

## Dependency Graph Visualization (`graph.py`)

Rendered with Graphviz (`rankdir=LR`, `splines=polyline`).

```
[USER INPUT]  ──(green dashed)──▶  [TOOL A]  ──(amber solid)──▶  [TOOL B]
   owner                             repo_id                        issue_id
   repo_name                         full_name
   title
```

| Edge type | Color | Meaning |
|---|---|---|
| Green dashed | `#16a34a` | Field provided directly by the user |
| Amber solid | `#d97706` | Field produced by a previous tool in the chain |
| Grey solid | `#94a3b8` | Control-flow only (no explicit field match) |

Each tool node shows its short name and the fields it produces, color-coded by service for Google tools (Gmail = red, Calendar = blue, Drive = green, Sheets = teal).

---

## File Structure

```
├── app.py            
├── tools.py          
├── dependency.py     
├── planner.py        
├── graph.py          
├── ui.py             
└── styles.py        
```

Each file has a single responsibility. `app.py` imports from all modules but contains no business logic itself.

---

## Example Outputs

### GitHub — "Merge a pull request"

**You provide:** `owner`, `repo_name`, `pr_number`

```
GITHUB_GET_A_REPOSITORY
  → GITHUB_GET_A_PULL_REQUEST
  → GITHUB_CHECK_IF_PULL_REQUEST_HAS_BEEN_MERGED
  → GITHUB_MERGE_A_PULL_REQUEST
```

| Step | Needs from you | Gets from prev step | Produces |
|---|---|---|---|
| GET_A_REPOSITORY | owner, repo_name | — | repo_id, full_name |
| GET_A_PULL_REQUEST | pr_number | repo_id | sha, mergeable, mergeable_state |
| CHECK_IF_...MERGED | — | repo_id, pr_number | merged (bool) |
| MERGE_A_PULL_REQUEST | — | sha, repo_id, pr_number | merged, sha |

---

### Google — "Reply to an email thread"

**You provide:** `user_id`, `thread_id`, `message_body`

```
GOOGLESUPER_FETCH_MESSAGE_BY_THREAD_ID
  → GOOGLESUPER_REPLY_TO_THREAD
```

| Step | Needs from you | Gets from prev step | Produces |
|---|---|---|---|
| FETCH_MESSAGE_BY_THREAD_ID | user_id, thread_id | — | message_id, headers, body |
| REPLY_TO_THREAD | message_body | thread_id, message_id | message_id, thread_id |

---

## Setup

```bash
# Install dependencies
pip install streamlit groq graphviz

# Set your Groq API key
export GROQ_API_KEY=your_key_here

# Run
streamlit run app.py
```

**Tool JSON schema** (one entry per tool):
```json
{
  "slug": "GITHUB_CREATE_AN_ISSUE",
  "description": "Creates a new issue in a repository.",
  "inputs": "owner,repo,title,body",
  "output": "IssueResponse",
  "produces_candidates": "issue_number,issue_id,url"
}
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| UI | Streamlit |
| LLM inference | Groq (`llama-3.3-70b-versatile`) |
| Graph algorithm | Custom BFS with field-name scoring |
| Visualisation | Graphviz (`python-graphviz`) |
| Tool catalogues | JSON (GitHub REST API + Google Workspace API) |

---

## Design Decisions

**Why BFS first, LLM second?**
BFS is deterministic and grounded in real field names from the tool catalog. The LLM is better at understanding intent but prone to hallucinating tool names. Using BFS to generate candidates and LLM to rank them combines the strengths of both.

**Why Groq with `temperature=0.0`?**
Dependency chains must be reproducible. Any randomness introduces hallucinated slugs or wrong ordering. Zero temperature makes the LLM behave as a deterministic ranker.

**Why a keyword pre-filter before BFS?**
Running BFS on all 500+ tools generates a graph with thousands of weak edges and meaningless chains. Filtering to ~20 relevant tools first makes BFS fast, precise, and scoped to the actual goal.

**Why Graphviz over a JS library?**
Streamlit's iframe sandbox blocks CDN-loaded JS libraries (vis-network, d3) at runtime. Graphviz renders to SVG natively via `st.graphviz_chart` with no network dependency.

## UI Flow
<img width="1500" height="723" alt="Home Page" src="https://github.com/user-attachments/assets/b4e6e2b6-3fe3-41d9-acf4-9a86982d1c5b" />
<img width="1438" height="769" alt="GitHub Planner Flow" src="https://github.com/user-attachments/assets/6a3bb8aa-b9d2-49ec-8ac9-75526522a5bb" />
<img width="1438" height="769" alt="GitHub Dependency Mapping" src="https://github.com/user-attachments/assets/e9d7eac9-1254-445a-8d93-ecd7550bb402" />
<img width="1438" height="568" alt="Google Dependency User Input" src="https://github.com/user-attachments/assets/42ba8582-d2bf-4c87-a3a2-71f9c1f8f85b" />
<img width="1438" height="512" alt="Google Dependency Chain" src="https://github.com/user-attachments/assets/24a340fe-23a7-4cf4-9e02-7690e3ad7317" />
<img width="1438" height="769" alt="BFS Chains then LLM picks up the best" src="https://github.com/user-attachments/assets/aa61cb06-47db-4a17-9c3a-62cf184851ac" />




