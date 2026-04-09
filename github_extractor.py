import json
import argparse
import sys
from pathlib import Path

COMMON_OUTPUT_KEYS = ["id", "node_id", "url", "html_url"]

RESOURCE_HINTS = {
    "ISSUE": ["id", "number", "url"],
    "PULL": ["id", "number", "url"],
    "PR": ["id", "number", "url"],
    "REPO": ["id", "name", "full_name"],
    "COMMIT": ["sha", "url"],
    "BRANCH": ["name", "commit_sha"],
    "FILE": ["path", "sha"],
    "RELEASE": ["id", "tag_name"],
    "COMMENT": ["id"],
    "WORKFLOW": ["id", "run_id"],
}


def guess_outputs(slug: str, output_ref: str) -> list[str]:
    slug_upper = slug.upper()
    ref_upper = (output_ref or "").upper()

    for key, fields in RESOURCE_HINTS.items():
        if key in slug_upper or key in ref_upper:
            return fields

    return COMMON_OUTPUT_KEYS


def extract_description(tool: dict) -> str:
    """
    Extract description from multiple possible locations.
    """

    desc = (
        tool.get("description")
        or tool.get("summary")
        or tool.get("details")
    )

    if not desc and isinstance(tool.get("operation"), dict):
        desc = tool["operation"].get("description")

    # Nested metadata fallback
    if not desc and isinstance(tool.get("metadata"), dict):
        desc = tool["metadata"].get("description")

    if not desc:
        desc = ""

    # White space normalize
    desc = str(desc).replace("\n", " ").strip()

    # Trim long descriptions
    if len(desc) > 200:
        desc = desc[:200] + "..."

    return desc

def extract_tool(tool: dict) -> dict:
    slug = tool.get("slug", "UNKNOWN")

    # Inputs → comma separated
    input_schema = tool.get("inputParameters", {})
    required_names = input_schema.get("required", []) or []
    inputs_str = ",".join(required_names)

    # Output reference
    output_schema = tool.get("outputParameters", {})
    output_ref = ""

    try:
        props = output_schema.get("properties", {})
        data_prop = props.get("data", {})
        ref = data_prop.get("$ref", "")
        if ref:
            output_ref = ref.split("/")[-1]
    except Exception:
        pass

    produces_candidates = guess_outputs(slug, output_ref)
    produces_str = ",".join(produces_candidates)

    # Description: For LLM context
    description = extract_description(tool)

    return {
        "slug": slug,
        "description": description,
        "inputs": inputs_str,
        "output": output_ref,
        "produces_candidates": produces_str
    }

def main():
    parser = argparse.ArgumentParser(description="Compact extractor for dependency graph")
    parser.add_argument("--input", "-i", required=True, help="Path to tools JSON")
    parser.add_argument("--output", "-o", default="", help="Output file path")
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"File not found: {args.input}")
        sys.exit(1)

    print(f"📂 Loading {input_path} ...")

    with open(input_path) as f:
        raw = json.load(f)

    if isinstance(raw, list):
        tools_raw = raw
    elif isinstance(raw, dict):
        for key in ("tools", "actions", "items", "data"):
            if key in raw and isinstance(raw[key], list):
                tools_raw = raw[key]
                break
        else:
            print("Could not find tools array")
            sys.exit(1)
    else:
        print("Invalid JSON format")
        sys.exit(1)

    print(f"Loaded {len(tools_raw)} tools")

    # Skiping deprecated tools
    tools_raw = [t for t in tools_raw if not t.get("isDeprecated", False)]

    extracted = [extract_tool(t) for t in tools_raw]

    # Output path
    if args.output:
        out_path = Path(args.output)
    else:
        out_path = input_path.parent / f"compressed_{input_path.stem}.json"

    with open(out_path, "w") as f:
        json.dump(extracted, f, indent=2)

    print(f"Written to {out_path}")

if __name__ == "__main__":
    main()