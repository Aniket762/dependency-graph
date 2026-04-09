import json
import argparse
import sys
from pathlib import Path

COMMON_OUTPUT_KEYS = ["id", "name"]

GOOGLE_RESOURCE_HINTS = {
    "EMAIL": ["id", "threadId"],
    "MESSAGE": ["id", "threadId"],
    "THREAD": ["id"],
    "DRAFT": ["id", "messageId"],
    "ATTACHMENT": ["attachmentId", "messageId"],
    "CALENDAR": ["id"],
    "EVENT": ["id", "htmlLink"],
    "MEETING": ["id", "hangoutLink"],
    "CONTACT": ["resourceName", "etag"],
    "LABEL": ["id", "name"],
}


def guess_outputs(slug: str, output_ref: str) -> list[str]:
    slug_upper = slug.upper()
    ref_upper = (output_ref or "").upper()

    for key, fields in GOOGLE_RESOURCE_HINTS.items():
        if key in slug_upper or key in ref_upper:
            return fields

    return COMMON_OUTPUT_KEYS


def extract_description(tool: dict) -> str:
    desc = (
        tool.get("description")
        or tool.get("summary")
        or tool.get("details")
    )

    if not desc and isinstance(tool.get("operation"), dict):
        desc = tool["operation"].get("description")

    if not desc and isinstance(tool.get("metadata"), dict):
        desc = tool["metadata"].get("description")

    if not desc:
        desc = ""

    desc = str(desc).replace("\n", " ").strip()

    if len(desc) > 200:
        desc = desc[:200] + "..."

    return desc


def extract_tool(tool: dict) -> dict:
    slug = tool.get("slug", "UNKNOWN")

    input_schema = tool.get("inputParameters", {})
    required_names = input_schema.get("required", []) or []
    inputs_str = ",".join(required_names)

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

    produces = guess_outputs(slug, output_ref)

    return {
        "slug": slug,
        "description": extract_description(tool),
        "inputs": inputs_str,
        "output": output_ref,
        "produces_candidates": ",".join(produces),
    }


def main():
    parser = argparse.ArgumentParser(description="Google tools extractor")
    parser.add_argument("--input", "-i", required=True)
    parser.add_argument("--output", "-o", default="")
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"File not found: {args.input}")
        sys.exit(1)

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

    tools_raw = [t for t in tools_raw if not t.get("isDeprecated", False)]

    extracted = [extract_tool(t) for t in tools_raw]

    out_path = (
        Path(args.output)
        if args.output
        else input_path.parent / f"compressed_{input_path.stem}.json"
    )

    with open(out_path, "w") as f:
        json.dump(extracted, f, indent=2)

    print(f"Written to {out_path}")


if __name__ == "__main__":
    main()