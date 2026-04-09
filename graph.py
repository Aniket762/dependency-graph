import graphviz

GOOGLE_COLORS: dict[str, tuple[str, str]] = {
    "GMAIL":    ("#fce8e6", "#c5221f"),
    "CALENDAR": ("#e8f0fe", "#1a73e8"),
    "DRIVE":    ("#e6f4ea", "#137333"),
    "SHEETS":   ("#e6f4ea", "#0f9d58"),
    "PEOPLE":   ("#fef7e0", "#f29900"),
    "CONTACTS": ("#fef7e0", "#f29900"),
}


def _short_label(slug: str) -> str:
    """Strip prefix and wrap at ~20 chars per line for readability."""
    short = slug.replace("GITHUB_", "").replace("GOOGLESUPER_", "")
    words = short.split("_")
    lines, cur = [], ""
    for w in words:
        if cur and len(cur) + len(w) > 20:
            lines.append(cur.rstrip("_"))
            cur = w + "_"
        else:
            cur += w + "_"
    if cur:
        lines.append(cur.rstrip("_"))
    return "\n".join(lines)


def _tool_colors(slug: str, platform: str) -> tuple[str, str]:
    if platform == "google":
        for key, (fill, border) in GOOGLE_COLORS.items():
            if key in slug:
                return fill, border
        return "#e8f0fe", "#1a73e8"   
    return "#dbeafe", "#1565c0"     


def build_graph(steps: list, all_user_inputs: list, platform: str) -> graphviz.Digraph:
    dot = graphviz.Digraph(
        graph_attr={
            "rankdir":  "LR",
            "splines":  "polyline", 
            "nodesep":  "0.7",
            "ranksep":  "1.4",
            "bgcolor":  "#ffffff",
            "pad":      "0.5",
            "fontname": "Helvetica",
        },
        node_attr={
            "fontname": "Helvetica",
            "fontsize": "11",
            "margin":   "0.3,0.2",
            "penwidth": "1.5",
        },
        edge_attr={
            "fontname": "Helvetica",
            "fontsize": "10",
            "penwidth": "2.0",
            "arrowsize": "0.8",
        },
    )

    user_label = "USER INPUT\n\n" + "\n".join(f"  {f}" for f in all_user_inputs)
    dot.node(
        "USER",
        label=user_label,
        shape="box",
        style="filled,rounded",
        fillcolor="#1a1a1a",
        fontcolor="#ffffff",
        color="#444444",
    )

    for step in steps:
        slug  = step["slug"]
        label = _short_label(slug)

        if step["produces"]:
            prod = "\n".join(f"  {p}" for p in step["produces"][:5])
            label += f"\n\nProduces:\n{prod}"

        fill, border = _tool_colors(slug, platform)
        dot.node(
            slug,
            label=label,
            shape="box",
            style="filled,rounded",
            fillcolor=fill,
            fontcolor="#111111",
            color=border,
        )

    # user-> tool edge
    for step in steps:
        if step["user_inputs"]:
            edge_label = "\n".join(step["user_inputs"])
            dot.edge(
                "USER",
                step["slug"],
                label=f" {edge_label} ",
                color="#16a34a",
                fontcolor="#166534",
                style="dashed",
                arrowhead="normal",
            )

    # tool -> tool edge
    for i, step in enumerate(steps):
        for prev in steps[:i]:
            shared = set(prev["produces"]) & set(step["chained_inputs"])
            if shared:
                edge_label = "\n".join(sorted(shared))
                dot.edge(
                    prev["slug"],
                    step["slug"],
                    label=f" {edge_label} ",
                    color="#d97706",
                    fontcolor="#92400e",
                    arrowhead="normal",
                )

    for i in range(1, len(steps)):
        prev_slug = steps[i - 1]["slug"]
        curr_slug = steps[i]["slug"]
        shared = set(steps[i - 1]["produces"]) & set(steps[i]["chained_inputs"])
        already_drawn = bool(shared)
        if not already_drawn:
            dot.edge(
                prev_slug,
                curr_slug,
                color="#94a3b8",
                fontcolor="#64748b",
                style="solid",
                arrowhead="normal",
                label=" (control flow) ",
            )

    return dot