#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

root = Path(__file__).resolve().parents[2]
required = [
    root / '.codex' / 'config.toml',
    root / '.codex' / 'hooks.json',
    root / '.codex' / 'prompts' / 'planner.md',
    root / '.codex' / 'scripts' / 'verify.py',
    root / '.codex' / 'scripts' / 'sync_linear.py',
    root / '.codex' / 'agents' / 'quality-reviewer.toml',
    root / '.codex' / 'agents' / 'performance-reviewer.toml',
    root / '.codex' / 'agents' / 'security-reviewer.toml',
    root / '.factory' / 'README.md',
    root / 'WORKFLOW.md',
]
missing = [str(path.relative_to(root)) for path in required if not path.exists()]
if missing:
    print('Missing factory scaffold files:')
    for item in missing:
        print(f'- {item}')
    sys.exit(1)
print('Factory scaffold OK')
