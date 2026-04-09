#!/bin/bash

set -e

if [ -z "$COMPOSIO_API_KEY" ]; then
	echo "Error: COMPOSIO_API_KEY is not set" >&2
	exit 1
fi

echo "Fetching OpenRouter API key..."
OPENROUTER_RESPONSE=$(curl -s -X POST "https://product-eng.hiring.composio.io/api/openrouter-key")

if command -v jq >/dev/null 2>&1; then
	OPENROUTER_API_KEY=$(echo "$OPENROUTER_RESPONSE" | jq -r '.apiKey')
else
	OPENROUTER_API_KEY=$(echo "$OPENROUTER_RESPONSE" | grep -o '"apiKey":"[^"]*' | cut -d'"' -f4)
fi

if [ -z "$OPENROUTER_API_KEY" ] || [ "$OPENROUTER_API_KEY" = "null" ]; then
	echo "Error: Failed to get openrouter api key" >&2
	echo "Response: $OPENROUTER_RESPONSE" >&2
	exit 1
fi

echo "Writing .env file..."
cat >.env <<EOF
COMPOSIO_API_KEY=$COMPOSIO_API_KEY
OPENROUTER_API_KEY=$OPENROUTER_API_KEY
EOF

echo "env file created"
