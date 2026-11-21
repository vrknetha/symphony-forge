# Pinned Autoreview boundary fixture

`scripts/autoreview` is copied unchanged from
https://github.com/openclaw/agent-skills/blob/ce14dcca09b3affb922ddcca11465619e67f5114/skills/autoreview/scripts/autoreview.
The upstream MIT license is in `LICENSE`.

The review-tree regression runs this helper through `forge close`, with only
Codex and GitHub replaced. Keep its validator unchanged. This fixture makes the
test independent of the network and the person's installed skills.
