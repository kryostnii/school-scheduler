#!/usr/bin/env bash
# Запуск GUI School Scheduler
# Использование: ./run_gui.sh
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
exec "$SCRIPT_DIR/venv/bin/python" -m app.main "$@"
