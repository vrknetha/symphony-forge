"""Release gate: python .github/release-notes-check.py <tag> <commit>, run in Forge's own checkout.

Fails when the release has no notes file, or when a shipped Forge file changed after the commit
that last changed the notes. The tag push hook runs the same check.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from forge import release_notes, repo  # noqa: E402

tag, commit = sys.argv[1:3]
sys.exit(release_notes.check(repo.root(), tag, commit) or print(f"Release {tag} notes cover {commit[:7]}."))
