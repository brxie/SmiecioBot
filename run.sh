#!/bin/bash

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

source "$SCRIPT_DIR/venv/bin/activate"

export TRIGGER_TIME="16:00"
export FB_EMAIL=""
export FB_PASSWORD=""
export THREAD_ID=""

python -u "$SCRIPT_DIR/main.py" 2>&1 | tee "$SCRIPT_DIR/$(date +%F).log"
