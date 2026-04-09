import os
import re
from groq import Groq

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# GitHub prompt
GITHUB_SYSTEM = (
    "You are a strict GitHub API dependency-chain planner.\n"
    "Golden rule: ALWAYS fetch/get an existing resource before creating or updating it.\n"
    "Never include CREATE_REPOSITORY unless the user explicitly wants to create a new repo.\n"
    "Output ONLY: TOOL_A -> TOOL_B -> TOOL_C — no explanation, no markdown."
)

# Google Prompt
GOOGLE_SYSTEM = (
    "You are a strict Google Workspace API dependency-chain planner "
    "(Gmail, Calendar, Drive, Sheets).\n"
    "Golden rule: ALWAYS fetch/get an existing resource before replying, "
    "updating, or acting on it.\n"
    "For reply-to-thread: first fetch the thread/message, then reply.\n"
    "Output ONLY: TOOL_A -> TOOL_B -> TOOL_C — no explanation, no markdown."
)


def build_ranking_prompt(candidates: list[list[str]], user_query: str) -> str:
    """Ask the LLM to pick the best chain from BFS-generated candidates."""
    numbered = "\n".join(
        f"{i+1}. {' -> '.join(c)}" for i, c in enumerate(candidates)
    )
    return f"""You are an API dependency-chain expert.

User goal: {user_query}

Candidate chains discovered by dependency analysis:
{numbered}

Select the single best chain that correctly and completely achieves the goal.

Rules:
- Choose the chain whose tool sequence best matches the goal's intent.
- Prefer shorter chains if equally valid.
- Return ONLY the chain exactly as written above (copy-paste the line).
- No explanation. No numbering. No markdown.

Chain:"""

GITHUB_USER_HINT = "repo_name, owner, title, body, issue_number, pr_number, branch"
GOOGLE_USER_HINT = (
    "user_id (='me'), calendar_id (='primary'), email_address, subject, "
    "message_body, thread_id, event_id, recipient_email, attendees, "
    "start_time, end_time"
)
GITHUB_FETCH_HINT = (
    "If goal involves an existing repo/issue/PR, "
    "start with GET_A_REPOSITORY or GET_A_PULL_REQUEST."
)
GOOGLE_FETCH_HINT = (
    "If goal involves an existing thread/event, "
    "start with FETCH_MESSAGE or GET_EVENT before replying/updating."
)

# When BFS did not find chain LLM needs to find the dependency
def build_fallback_prompt(filtered_tools: list, user_query: str, platform: str) -> str:
    tools_text = "\n".join(
        f"  {t['slug']}\n"
        f"    REQUIRES : {t['inputs'] or 'nothing'}\n"
        f"    PRODUCES : {t['produces_candidates'] or 'nothing'}"
        for t in filtered_tools
    )
    user_hint  = GITHUB_USER_HINT  if platform == "github" else GOOGLE_USER_HINT
    fetch_hint = GITHUB_FETCH_HINT if platform == "github" else GOOGLE_FETCH_HINT

    return f"""You are a {platform.upper()} API dependency-chain expert.

USER GOAL: {user_query}

AVAILABLE TOOLS:
{tools_text}

RULES:
1. FETCH BEFORE ACT: {fetch_hint}
2. SATISFY REQUIRES: every tool's REQUIRES must be covered by user fields
   ({user_hint}) OR a prior tool's PRODUCES.
3. NO UNNECESSARY TOOLS — every step must be essential.
   Do NOT include LIST/SEARCH tools unless the goal explicitly needs them.
4. Return UP TO 5 steps if needed; prefer the shortest valid chain.
5. Output ONLY: TOOL_ONE -> TOOL_TWO -> TOOL_THREE

Chain:"""

def _call_groq(prompt: str, system: str) -> str:
    try:
        res = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": system},
                {"role": "user",   "content": prompt},
            ],
            temperature=0.0,
        )
        raw = res.choices[0].message.content.strip()
        raw = re.sub(r'^(Chain|Answer|Result|\d+\.)\s*', '', raw, flags=re.IGNORECASE)
        return raw.split("\n")[0].strip()
    except Exception as e:
        return f"Error: {e}"

# LLM picks up best chain from BFS
def rank_plan(candidates: list[list[str]], user_query: str, platform: str) -> str:
    system = GITHUB_SYSTEM if platform == "github" else GOOGLE_SYSTEM
    prompt = build_ranking_prompt(candidates, user_query)
    return _call_groq(prompt, system)

# LLM builds chain from scratch
def llm_plan(filtered_tools: list, user_query: str, platform: str) -> str:
    system = GITHUB_SYSTEM if platform == "github" else GOOGLE_SYSTEM
    prompt = build_fallback_prompt(filtered_tools, user_query, platform)
    return _call_groq(prompt, system)