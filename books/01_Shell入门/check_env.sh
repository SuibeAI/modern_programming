#!/usr/bin/env bash
set -euo pipefail

echo "Current directory: $(pwd)"
echo "PATH: ${PATH}"
echo "PYTHONPATH: ${PYTHONPATH:-<not set>}"
echo "Git version: $(git --version)"
echo "Python version: $(python3 --version)"
echo "python3 path: $(which python3)"
echo "pip3 path: $(which pip3 || echo '<not found>')"
