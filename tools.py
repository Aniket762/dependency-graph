import json
import streamlit as st

@st.cache_data
def load_tools(path: str) -> list:
    with open(path) as f:
        tools = json.load(f)
    for t in tools:
        t.setdefault("inputs", "")
        t.setdefault("produces_candidates", "")
        t.setdefault("description", "")
        t["inputs_list"]   = [x.strip() for x in t["inputs"].split(",")              if x.strip()]
        t["produces_list"] = [x.strip() for x in t["produces_candidates"].split(",") if x.strip()]
    return tools

GITHUB_INTENTS: dict[str, list[str]] = {
    "create issue":  ["issue", "create", "repo", "get"],
    "close issue":   ["issue", "close", "update", "repo", "get"],
    "comment pr":    ["pull", "comment", "repo", "get"],
    "merge pr":      ["pull", "merge", "repo", "get"],
    "create pr":     ["pull", "create", "branch", "repo", "get"],
    "get repo":      ["repo", "get"],
    "list issues":   ["issue", "list", "repo", "get"],
}

GOOGLE_INTENTS: dict[str, list[str]] = {
    "send email":          ["send", "message", "email", "gmail", "compose"],
    "compose email":       ["send", "message", "email", "gmail", "compose"],
    "reply email":         ["reply", "message", "thread", "email", "gmail", "fetch"],
    "reply to email":      ["reply", "message", "thread", "email", "gmail", "fetch"],
    "smart auto reply":    ["reply", "message", "thread", "email", "gmail", "fetch"],
    "forward email":       ["forward", "message", "email", "gmail"],
    "draft email":         ["draft", "message", "email", "gmail"],
    "search email":        ["search", "message", "email", "gmail", "list"],
    "find email":          ["search", "message", "email", "gmail", "list"],
    "unread email":        ["list", "message", "email", "gmail", "unread"],
    "label email":         ["label", "message", "email", "gmail", "modify"],
    "save attachment":     ["attachment", "message", "email", "gmail"],
    "contact lookup":      ["contact", "people", "email"],
    "schedule meeting":    ["calendar", "event", "create", "insert", "attendee"],
    "create event":        ["calendar", "event", "create", "insert"],
    "reschedule meeting":  ["calendar", "event", "update", "patch", "get"],
    "cancel meeting":      ["calendar", "event", "delete", "get"],
    "add attendee":        ["calendar", "event", "update", "patch", "attendee"],
    "daily agenda":        ["calendar", "event", "list", "email", "send"],
    "weekly summary":      ["calendar", "event", "list", "email", "send"],
    "meeting reminder":    ["calendar", "event", "list", "email", "send"],
    "email to meeting":    ["calendar", "event", "create", "message", "email"],
    "follow up reminder":  ["calendar", "event", "create", "message", "email"],
    "upload file":         ["drive", "file", "upload", "create"],
    "share file":          ["drive", "file", "permission", "share"],
    "create sheet":        ["sheets", "spreadsheet", "create"],
    "update sheet":        ["sheets", "spreadsheet", "values", "update"],
}

GITHUB_USER_FIELDS: set[str] = {
    "repo_name", "owner", "repo", "title", "body", "issue_number", "pr_number",
    "pull_number", "comment", "comment_body", "branch", "head", "base", "label",
    "assignee", "milestone", "content", "commit_sha", "ref", "tag", "release_id",
    "file_path", "message", "name", "description", "private",
}

GOOGLE_USER_FIELDS: set[str] = {
    "user_id", "calendar_id", "email_address", "subject", "message_body", "body",
    "to", "cc", "bcc", "thread_id", "event_id", "attendees", "start_time", "end_time",
    "location", "summary", "description", "file_id", "spreadsheet_id", "sheet_id",
    "range", "values", "recipient_email", "query", "label_id", "rule_id",
    "contact_id", "name", "title", "attachment",
}


CREATE_WORDS = {"create", "send", "compose", "add", "schedule","insert", "reply", "forward", "draft", "cancel", "delete"}

CREATE_TOOL_WORDS = {"create", "send", "compose", "add","insert", "delete", "remove", "reply", "forward"}


# Top-K nbrs
def keyword_filter(user_query: str, tools: list, intent_map: dict, k: int = 20) -> list:
    q = user_query.lower()

    keywords: list[str] = []
    best_key, best_hit = None, 0
    for key, kws in intent_map.items():
        hits = sum(1 for word in key.split() if word in q)
        if hits > best_hit:
            best_hit, best_key = hits, key
    if best_key:
        keywords = intent_map[best_key]
    if not keywords:
        keywords = [w for w in q.split() if len(w) > 3][:5] or ["get", "list"]

    is_create_query = any(w in q for w in CREATE_WORDS)

    scored: list[tuple[int, dict]] = []
    for t in tools:
        slug = t["slug"].lower()
        is_create_tool = any(w in slug for w in CREATE_TOOL_WORDS)
        if is_create_tool and not is_create_query:
            continue
        score  = sum(3 for kw in keywords if kw in slug)
        score += sum(1 for kw in keywords if kw in t["inputs"].lower())
        score += sum(1 for kw in keywords if kw in t["produces_candidates"].lower())
        if score > 0:
            scored.append((score, t))

    scored.sort(reverse=True, key=lambda x: x[0])
    return [t for _, t in scored[:k]]


def validate_chain(raw_plan: str, slug_map: dict) -> list[str]:
    return [s.strip() for s in raw_plan.split("->") if s.strip() in slug_map]


def analyze_chain(chain: list[str], slug_map: dict, user_fields: set) -> tuple[list, list]:
    available = set(user_fields)
    steps: list[dict] = []
    all_user_inputs: list[str] = []

    for slug in chain:
        tool = slug_map.get(slug)
        if not tool:
            continue

        requires    = set(tool["inputs_list"])
        produces    = set(tool["produces_list"])
        user_inp    = sorted(requires & user_fields)
        chained_inp = sorted(requires - user_fields)
        missing     = sorted(requires - available)

        for f in user_inp:
            if f not in all_user_inputs:
                all_user_inputs.append(f)

        steps.append({
            "slug":           slug,
            "user_inputs":    user_inp,
            "chained_inputs": chained_inp,
            "produces":       sorted(produces),
            "missing":        missing,
        })
        available |= produces

    return steps, all_user_inputs