#!/usr/bin/env bash
set -euo pipefail
pytest -v --cov=task_scaffolder --cov-report=term-missing
