#!/usr/bin/env bash
# Helper: green two-line PS1
# Usage:
#  - Source this file from your shell to preview: source dotfiles/ps1-green-two-line.sh
#  - To persist, append the export line into your ~/.bashrc (see instructions below)

export PS1="\n\[\e[32m\]\u@\h:\[\e[01;36m\]\w\[\e[0m\]\n\$ "

# Optional: enable PROMPT_DIRTRIM to shorten long paths (keep only last 2 components)
# PROMPT_DIRTRIM=2
