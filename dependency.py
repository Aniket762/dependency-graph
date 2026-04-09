from collections import defaultdict, deque

_VERBS = {
    "GET", "LIST", "CREATE", "UPDATE", "DELETE",
    "ADD", "REMOVE", "SET", "CHECK", "ENABLE", "DISABLE",
    "FETCH", "SEND", "REPLY", "FORWARD", "MERGE", "CLOSE",
    "PATCH", "INSERT", "SEARCH", "UPLOAD", "SHARE",
}

_DOMAIN_ALIASES = {
    "PR": "PULL",
}


def _extract_domain(slug: str) -> str:
    """Return the first non-verb token after the tool prefix (GITHUB_ / GOOGLESUPER_)."""
    for prefix in ("GITHUB_", "GOOGLESUPER_"):
        if slug.startswith(prefix):
            slug = slug[len(prefix):]
            break

    for part in slug.split("_"):
        if part not in _VERBS:
            return _DOMAIN_ALIASES.get(part, part)

    return "GENERIC"


def _match_score(output_key: str, input_key: str) -> int:
    o = output_key.lower().strip()
    i = input_key.lower().strip()

    if i.endswith(f"_{o}"):
        return 3
    if i == o:
        return 2
    if o == "id" and i.endswith("_id"):
        return 1
    return 0


def build_graph(tools: list) -> dict[str, list[tuple[str, int]]]:
    # Index: input_field
    input_index: dict[str, list[str]] = defaultdict(list)
    tool_domain: dict[str, str] = {}

    for tool in tools:
        slug   = tool["slug"]
        domain = _extract_domain(slug)
        tool_domain[slug] = domain

        for inp in tool.get("inputs", "").split(","):
            inp = inp.strip().lower()
            if inp:
                input_index[inp].append(slug)

    # Relax Regex Filter
    unique_domains = set(tool_domain.values())
    relax_domain = len(unique_domains) > 2 or len(tools) < 6

    graph: dict[str, list[tuple[str, int]]] = defaultdict(list)

    for tool in tools:
        producer        = tool["slug"]
        producer_domain = tool_domain[producer]
        outputs         = tool.get("produces_candidates", "").split(",")

        for out in outputs:
            out = out.strip().lower()
            if not out:
                continue

            candidates = [out, f"{out}_id", f"{out}_number", f"{out}_name", f"{out}s"]

            for cand in candidates:
                for consumer in input_index.get(cand, []):
                    if consumer == producer:
                        continue
                    if not relax_domain and tool_domain[consumer] != producer_domain:
                        continue
                    score = _match_score(out, cand)
                    if score > 0:
                        graph[producer].append((consumer, score))

    return dict(graph)


def find_all_flows(
    graph: dict,
    max_flows: int = 5,
    min_length: int = 2,
    max_length: int = 5,
) -> list[list[str]]:

    starts = sorted(graph.keys(), key=lambda s: -len(graph[s]))

    seen_paths: set[str] = set()
    flows: list[list[str]] = []

    for start in starts:
        if len(flows) >= max_flows:
            break

        queue: deque[tuple[str, list[str]]] = deque([(start, [start])])

        while queue and len(flows) < max_flows:
            node, path = queue.popleft()

            if min_length <= len(path) <= max_length:
                key = " -> ".join(path)
                if key not in seen_paths:
                    seen_paths.add(key)
                    flows.append(list(path))

            if len(path) < max_length:
                neighbors = sorted(
                    graph.get(node, []),
                    key=lambda x: -x[1],  
                )
                # Cycle Detection
                for neighbor, _ in neighbors:
                    if neighbor not in path:   
                        queue.append((neighbor, path + [neighbor]))

    return flows