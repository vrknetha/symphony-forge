"""Claude Code's plugin CLI stand-in shared by command tests."""

import json
import sys

from conftest import _install


CLAUDE = """#!{python}
import json, pathlib, sys
here = pathlib.Path(__file__).resolve().parent
args = sys.argv[1:]
with open(here / 'claude-calls.jsonl', 'a', encoding='utf-8') as log:
    log.write(json.dumps(args) + '\\n')
state = json.loads((here / 'claude-state.json').read_text('utf-8'))
if args == ['--version']:
    print(state['version'] + ' (Claude Code)')
elif args == ['plugin', 'marketplace', 'list', '--json']:
    source = state['marketplace'] if isinstance(state['marketplace'], str) else 'vrknetha/symphony-forge'
    print(json.dumps([{{'name': 'forge', 'source': 'github', 'repo': source}}] if state['marketplace'] else []))
elif args == ['plugin', 'list', '--json']:
    print(json.dumps([{{'id': 'forge@forge', 'version': state['installed'], 'scope': 'user', 'enabled': True}}] if state['installed'] else []))
elif state['offline']:
    sys.stderr.write('Network unavailable\\nretry later\\n')
    sys.exit(1)
"""


def _claude(repo, *, marketplace=False, installed='', offline=False, version='2.1.291'):
    (repo.bin / 'claude-state.json').write_text(json.dumps({
        'marketplace': marketplace, 'installed': installed,
        'offline': offline, 'version': version}), encoding='utf-8')
    _install(repo.bin, 'claude', CLAUDE.format(python=sys.executable))


def _calls(repo):
    log = repo.bin / 'claude-calls.jsonl'
    return [json.loads(line) for line in log.read_text('utf-8').splitlines()] if log.exists() else []
