---
authors: ['björn']
date: '2026-03-20T12:31:05+01:00'
lastmod: '2026-03-20T13:52:35+01:00'
location: Sweden
full: true
title: 'How I configure beads for new projects'
tags: ['beads']
daily: ['2026-03-20']
series: []
---
I tweak the default beads setup to work with Claude instead of the generic agent integration.

As of beads 0.61.0, this is what I run:

```shell
# configure agents later
bd init --prefix bt --shared-server --skip-agents

# remove credential key that bd init auto-commits
git rm --cached .beads/.beads-credential-key
echo .beads-credential-key >> .beads/.gitignore

# setup a CLAUDE.md and configure claude hooks to re-prime beads
bd setup claude --project
bd hooks install

# move local settings to project settings
mv .claude/settings{.local,}.json
git add .claude/settings.json CLAUDE.md

# amend init commit so .beads-credential-key never enters git
git commit --amend -CHEAD

# share beads data alongside your git repo
bd dolt remote add origin git+ssh://git@github.com/you/repo.git
echo -e 'sync:\n  git-remote: git+ssh://git@github.com/you/repo.git' >> .beads/config.yaml
```

The key thing is `--skip-agents` and then `bd setup claude --project` instead, so you get Claude-specific hooks rather than the generic agent integration. The [dolt remote lines]({{< relref "2026-03-20-configure-beads-dolt-to-share-via-git.md" >}}) are so your beads data gets stored alongside your git repo.
