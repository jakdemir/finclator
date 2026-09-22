#!/bin/bash
# Restart Ollama in the foreground-less way with the tuned server settings (8 slots, flash attention, q8 KV).
# Usage: scripts/ollama_serve.sh   (logs to data/ollama.log)
cd "$(dirname "$0")/.."
launchctl bootout "gui/$(id -u)/com.finclator.ollama" 2>/dev/null || true
pkill -f "ollama serve" 2>/dev/null || true
sleep 2
OLLAMA_NUM_PARALLEL=8 OLLAMA_KEEP_ALIVE=8h OLLAMA_FLASH_ATTENTION=1 OLLAMA_KV_CACHE_TYPE=q8_0 \
  nohup /opt/homebrew/bin/ollama serve >> data/ollama.log 2>&1 &
for i in $(seq 1 30); do curl -sf http://localhost:11434/api/tags >/dev/null && break; sleep 1; done
curl -sf http://localhost:11434/api/version && echo " ollama up (8 slots)"
