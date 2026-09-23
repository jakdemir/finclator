#!/bin/bash
# Launch Ollama (8 slots) + the resumable local classifier + admin page as macOS launchd jobs so they survive the
# Hermes/desktop session. Idempotent: re-running bootouts old jobs first. Stop with: scripts/stop_run.sh
set -e
cd "$(dirname "$0")/.."
ROOT=$(pwd)
MODEL=${FINCLATOR_MODEL:-qwen3.6-local:35b-a3b-q4_K_M}
DOM="gui/$(id -u)"
mkdir -p data

launchctl bootout "$DOM/com.finclator.ollama"   2>/dev/null || true
launchctl bootout "$DOM/com.finclator.classify" 2>/dev/null || true
launchctl bootout "$DOM/com.finclator.admin"    2>/dev/null || true
pkill -f "ollama serve" 2>/dev/null || true
sleep 1

plist() {  # name, log, env (K=V ...), -- program args
  local name=$1 log=$2; shift 2
  local env=""
  while [ "$1" != "--" ]; do env="$env<key>${1%%=*}</key><string>${1#*=}</string>"; shift; done
  shift
  local args=""
  for a in "$@"; do args="$args<string>$a</string>"; done
  local f="/tmp/$name.plist"
  cat > "$f" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
<key>Label</key><string>$name</string>
<key>WorkingDirectory</key><string>$ROOT</string>
<key>EnvironmentVariables</key><dict><key>PATH</key><string>/opt/homebrew/bin:/usr/bin:/bin</string>$env</dict>
<key>ProgramArguments</key><array>$args</array>
<key>StandardOutPath</key><string>$log</string><key>StandardErrorPath</key><string>$log</string>
<key>RunAtLoad</key><true/>
</dict></plist>
EOF
  launchctl bootstrap "$DOM" "$f"
}

plist com.finclator.ollama data/ollama.log OLLAMA_NUM_PARALLEL=8 OLLAMA_KEEP_ALIVE=8h OLLAMA_FLASH_ATTENTION=1 OLLAMA_KV_CACHE_TYPE=q8_0 \
  -- /opt/homebrew/bin/ollama serve
for i in $(seq 1 20); do curl -sf http://localhost:11434/api/tags >/dev/null && break; sleep 1; done
plist com.finclator.classify data/classify_run.out FINCLATOR_MODEL_BASE_URL=http://localhost:11434/v1 FINCLATOR_MODEL=$MODEL \
  FINCLATOR_WORKERS=8 FINCLATOR_TERSE=1 FINCLATOR_BATCH_SIZE=4 PYTHONPATH=. -- "$ROOT/.venv/bin/python" scripts/classify_run.py
# Admin publishes the same tag classify stores under: "<model>+jev" (models.classifier_model with the gate on).
plist com.finclator.admin data/admin.out FINCLATOR_MODEL=$MODEL -- "$ROOT/.venv/bin/python" -m src.admin
sleep 2
launchctl list | grep com.finclator
