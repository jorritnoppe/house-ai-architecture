#!/usr/bin/env bash
set -euo pipefail

PROMPT=$(cat <<'EOF'
You are the house AI storyteller.

Write a calm, immersive spoken story of about 5000 short lines.

Rules:
- Use sensor data
- Make it pleasant to hear over a speaker
- Use short, simple spoken sentences
- Keep the pacing relaxed
- No bullets, no numbering
- No chapter titles
- No explanations before or after
- Just the story text
- Theme: a peaceful magical evening journey with gentle mystery
EOF
)

MODEL="phi3:latest"

RAW_RESPONSE=$(curl -s http://127.0.0.1:11434/api/generate \
  -H "Content-Type: application/json" \
  -d "$(jq -n \
    --arg model "$MODEL" \
    --arg prompt "$PROMPT" \
    '{model:$model,prompt:$prompt,stream:false}')")

echo "=== OLLAMA RAW RESPONSE ==="
echo "$RAW_RESPONSE"
echo "==========================="

STORY=$(echo "$RAW_RESPONSE" | jq -r '
  if .response and (.response | length > 0) then
    .response
  elif .error then
    "ERROR: " + .error
  else
    empty
  end
')

if [ -z "${STORY:-}" ]; then
  echo "No story text returned from Ollama."
  exit 1
fi

if [[ "$STORY" == ERROR:* ]]; then
  echo "$STORY"
  exit 1
fi

#!/usr/bin/env bash
set -euo pipefail

MODEL="phi3:latest"

PROMPT="Write a calm spoken story of about 100 short lines. Keep sentences short."

echo "Generating story..."

STORY=$(curl -s http://127.0.0.1:11434/api/generate \
  -H "Content-Type: application/json" \
  -d "$(jq -n --arg model "$MODEL" --arg prompt "$PROMPT" '{model:$model,prompt:$prompt,stream:false}')" \
  | jq -r '.response')

[ -n "$STORY" ] || { echo "Empty story"; exit 1; }

echo "Splitting story into chunks..."

# Split into chunks of ~500 chars
CHUNKS=$(echo "$STORY" | fold -w 500 -s)

echo "Playing on bathroom speaker..."

while IFS= read -r CHUNK; do
  echo "Sending chunk..."

  curl -s -X POST http://127.0.0.1:8000/house/speak/bathroom \
    -H "Content-Type: application/json" \
    -d "$(jq -n \
      --arg text "$CHUNK" \
      --argjson volume 20 \
      '{text:$text,volume:$volume}')" > /dev/null

  sleep 1   # small delay between chunks
done <<< "$CHUNKS"

echo "Done."
