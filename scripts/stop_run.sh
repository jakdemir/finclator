#!/bin/bash
# Stop the launchd jobs started by scripts/start_run.sh (classifier is resumable; re-run start_run.sh to continue).
DOM="gui/$(id -u)"
for j in classify admin ollama; do launchctl bootout "$DOM/com.finclator.$j" 2>/dev/null && echo "stopped $j"; done
