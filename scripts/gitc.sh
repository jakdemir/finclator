#!/bin/bash
# usage: gitc.sh "<message>" [paths...]  — add, commit, push in one gated-safe script
cd ~/projects/finclator
msg="$1"; shift
if [ $# -gt 0 ]; then git add "$@"; else git add -A; fi
git commit -q -m "$msg" && git push -q origin main && git log --oneline -1
git status --short | head
