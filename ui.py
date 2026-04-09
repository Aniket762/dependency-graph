import streamlit as st
from styles import GITHUB_SVG, GOOGLE_SVG


def render_landing() -> None:
    st.markdown(
        "<h1 style='text-align:center;font-size:2.3rem;font-weight:700;"
        "letter-spacing:-0.5px;margin-bottom:6px;'>API Dependency Planner</h1>"
        "<p style='text-align:center;color:#888;font-size:15px;margin-bottom:44px;'>"
        "Select a platform to map your dependency chain</p>",
        unsafe_allow_html=True,
    )

    col_gh, col_go = st.columns(2, gap="large")

    with col_gh:
        st.markdown(
            f"""<div class="platform-card">
              {GITHUB_SVG}
              <div class="card-name">GitHub</div>
              <div class="card-sub">Issues · Pull Requests · Repos · Merges</div>
            </div>""",
            unsafe_allow_html=True,
        )
        if st.button("github", key="pick_github", use_container_width=True):
            st.session_state["platform"] = "github"
            st.rerun()

    with col_go:
        st.markdown(
            f"""<div class="platform-card">
              {GOOGLE_SVG}
              <div class="card-name">Google Workspace</div>
              <div class="card-sub">Gmail · Calendar · Drive · Sheets</div>
            </div>""",
            unsafe_allow_html=True,
        )
        if st.button("google", key="pick_google", use_container_width=True):
            st.session_state["platform"] = "google"
            st.rerun()

def render_header(platform: str) -> None:
    logo  = GITHUB_SVG if platform == "github" else GOOGLE_SVG
    title = "GitHub"   if platform == "github" else "Google Workspace"

    if st.button("← Back", key="back_btn"):
        st.session_state.pop("platform",    None)
        st.session_state.pop("plan_result", None)
        st.rerun()

    st.markdown(
        f"""<div style="display:flex;align-items:center;gap:14px;margin:8px 0 2px;">
          <div style="width:36px;height:36px;flex-shrink:0;">{logo}</div>
          <h2 style="margin:0;font-size:1.5rem;font-weight:700;">
            {title} — Dependency Planner
          </h2>
        </div>
        <p style="color:#888;margin:0 0 24px 50px;font-size:13px;">
          Describe your goal and get the full API dependency chain.
        </p>""",
        unsafe_allow_html=True,
    )


GITHUB_EXAMPLES = [
    "Create an issue", "Merge a pull request",
    "Comment on a PR", "Close an issue", "Create a pull request",
]

GOOGLE_EXAMPLES = [
    "Send an email", "Reply to an email thread",
    "Schedule a meeting", "Cancel a meeting",
    "Daily agenda email", "Forward an email",
    "Draft an email", "Add attendees to a meeting",
]


def render_query_input(platform: str) -> str:
    examples = GITHUB_EXAMPLES if platform == "github" else GOOGLE_EXAMPLES

    st.markdown(
        "<p style='font-size:13px;color:#555;margin-bottom:8px;'>Quick examples</p>",
        unsafe_allow_html=True,
    )

    cols = st.columns(len(examples))
    for i, ex in enumerate(examples):
        if cols[i].button(ex, key=f"pill_{platform}_{i}", use_container_width=True):
            st.session_state["prefill"] = ex
            st.rerun()                    

    default = st.session_state.pop("prefill", "")
    query = st.text_input(
        "Your goal",
        value=default,
        placeholder="e.g. reply to an email thread",
        label_visibility="collapsed",
    )
    return query

def render_results(chain: list, steps: list, all_user_inputs: list) -> None:
    st.divider()
    st.markdown("#### 📋 What you need to provide")
    if all_user_inputs:
        st.markdown(
            " ".join(f'<span class="chip">{f}</span>' for f in all_user_inputs),
            unsafe_allow_html=True,
        )
    else:
        st.info("No manual inputs required beyond defaults.")

    st.markdown("#### 🔗 Dependency Chain")
    arrow = " &nbsp;→&nbsp; "
    chain_html = arrow.join(
        f'<span style="color:#93c5fd">{s}</span>' for s in chain
    )
    st.markdown(f'<div class="chain-box">{chain_html}</div>', unsafe_allow_html=True)

    st.markdown("#### 🧩 Steps")
    for i, step in enumerate(steps, 1):
        with st.expander(f"Step {i} — {step['slug']}"):
            _render_step(step)

    st.markdown("#### 📊 Dependency Flow Graph")
    st.caption("🟢 dashed = user input &nbsp;|&nbsp; 🟡 solid = chained data &nbsp;|&nbsp; ⚪ grey = control flow")


def _render_step(step: dict) -> None:
    def badges(items: list, css_class: str) -> str:
        return " ".join(f'<span class="badge {css_class}">{f}</span>' for f in items)

    if step["user_inputs"]:
        st.markdown("**You provide:**")
        st.markdown(badges(step["user_inputs"], "badge-user"), unsafe_allow_html=True)

    if step["chained_inputs"]:
        st.markdown("**From previous step:**")
        st.markdown(badges(step["chained_inputs"], "badge-chain"), unsafe_allow_html=True)

    if step["produces"]:
        st.markdown("**This step produces:**")
        st.markdown(badges(step["produces"], "badge-produces"), unsafe_allow_html=True)

    if step["missing"]:
        st.markdown(
            badges([f"⚠ {f}" for f in step["missing"]], "badge-warn"),
            unsafe_allow_html=True,
        )