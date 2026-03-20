---
authors: ['björn']
date: '2026-03-20T12:31:05+01:00'
lastmod: '2026-03-20T12:31:05+01:00'
location: Sweden
full: false  # set to true if the full thing should be shown in listings
title: 'Configure beads dolt to share via git'
tags: ['beads']
daily: ['2026-03-20']
series: []
---
Beads with dolt [store data](https://github.com/steveyegge/beads/blob/main/docs/DOLT.md) in git refs, not branches, and won't share it anywhere until you manually configure a remote.

After `bd init`, your dolt data only exists locally. You can check with `bd dolt remote list` which will show "No remotes configured."

<!--more-->

Point it at your existing git repo:

```shell
bd dolt remote add origin git+ssh://git@github.com/youruser/yourrepo.git
```

Then push and verify:

```shell
bd dolt push
git ls-remote origin 'refs/dolt/*'
# 52689c0ae7...  refs/dolt/data
```

I've seen `refs/` used for GitHub PRs before (`refs/pr/<num>/head`) but I haven't looked into how any of it actually works. For now, seeing `refs/dolt/data` show up in `git ls-remote` is enough to make me comfortable that my data exists somewhere.

To avoid doing this manually on every machine, add the remote to `.beads/config.yaml`:

```yaml
sync:
  git-remote: git+ssh://git@github.com/youruser/yourrepo.git
```

Anyone cloning the repo can then run `bd bootstrap` and `bd dolt push / pull` will just work.
