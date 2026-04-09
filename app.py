import streamlit as st
# Streamlit Config
st.set_page_config(
    page_title="API Dependency Planner",
    page_icon="🔗",
    layout="wide",
    initial_sidebar_state="collapsed",
)
from styles     import GLOBAL_CSS
from tools      import (
    load_tools,
    GITHUB_INTENTS, GOOGLE_INTENTS,
    GITHUB_USER_FIELDS, GOOGLE_USER_FIELDS,
    keyword_filter, validate_chain, analyze_chain,
)
from dependency import build_graph, find_all_flows
from planner    import rank_plan, llm_plan
from graph      import build_graph as build_viz
from ui         import render_landing, render_header, render_query_input, render_results


st.markdown(GLOBAL_CSS, unsafe_allow_html=True)

github_tools = load_tools("data/compressed_github_tools.json")
google_tools = load_tools("data/compressed_googlesuper_tools.json")

GITHUB_SLUG_MAP = {t["slug"]: t for t in github_tools}
GOOGLE_SLUG_MAP = {t["slug"]: t for t in google_tools}

platform: str | None = st.session_state.get("platform")

if not platform:
    render_landing()
    st.stop()

render_header(platform)

tools_list  = github_tools       if platform == "github" else google_tools
slug_map    = GITHUB_SLUG_MAP    if platform == "github" else GOOGLE_SLUG_MAP
intent_map  = GITHUB_INTENTS     if platform == "github" else GOOGLE_INTENTS
user_fields = GITHUB_USER_FIELDS if platform == "github" else GOOGLE_USER_FIELDS

user_query = render_query_input(platform)

st.markdown("")
if st.button("Generate Dependency Plan →", type="primary", use_container_width=True):
    if not user_query.strip():
        st.warning("Please enter a goal.")
        st.stop()
    
    with st.spinner("Filtering tools…"):
        filtered = keyword_filter(user_query, tools_list, intent_map)

    if not filtered:
        st.error("No relevant tools found — try rephrasing.")
        st.stop()

    with st.spinner("Running dependency graph analysis…"):
        sub_graph       = build_graph(filtered)
        bfs_candidates  = find_all_flows(sub_graph, max_flows=5)

    if bfs_candidates:
        with st.spinner(f"BFS found {len(bfs_candidates)} candidate(s) — ranking with LLM…"):
            raw = rank_plan(bfs_candidates, user_query, platform)
        source_label = "BFS + LLM ranked"
    else:
        with st.spinner("No BFS chains found — planning with LLM directly…"):
            raw = llm_plan(filtered, user_query, platform)
        source_label = "LLM direct"

    if raw.startswith("Error"):
        st.error(raw)
        st.stop()

    chain = validate_chain(raw, slug_map)

    if not chain and bfs_candidates:
        chain = bfs_candidates[0]
        source_label += " (fallback to top BFS chain)"

    if not chain:
        st.error("Could not produce a valid chain. Try rephrasing.")
        with st.expander("Raw model output"):
            st.code(raw)
        st.stop()

    steps, all_user_inputs = analyze_chain(chain, slug_map, user_fields)

    st.session_state["plan_result"] = {
        "chain":           chain,
        "steps":           steps,
        "all_user_inputs": all_user_inputs,
        "platform":        platform,
        "query":           user_query,
        "source":          source_label,
        "bfs_candidates":  bfs_candidates,
    }


result = st.session_state.get("plan_result")
if result and result["platform"] == platform:
    src = result.get("source", "")
    color = "#166534" if "BFS" in src else "#92400e"
    bg    = "#dcfce7" if "BFS" in src else "#fef3c7"
    st.markdown(
        f'<span style="background:{bg};color:{color};border-radius:6px;'
        f'padding:3px 10px;font-size:11px;font-weight:600;">'
        f'Source: {src}</span>',
        unsafe_allow_html=True,
    )

    render_results(result["chain"], result["steps"], result["all_user_inputs"])

    if result.get("bfs_candidates"):
        with st.expander(f"🔍 All BFS candidate chains ({len(result['bfs_candidates'])})"):
            for i, c in enumerate(result["bfs_candidates"], 1):
                st.code(f"{i}. {' -> '.join(c)}")

    dot = build_viz(result["steps"], result["all_user_inputs"], platform)
    st.graphviz_chart(dot, use_container_width=True)