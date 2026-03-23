---
authors: ['björn']
date: '2026-03-23T16:02:49+01:00'
lastmod: '2026-03-23T16:02:49+01:00'
location: Sweden
full: true
title: 'How to manually restore a dolt db from its git remote'
tags: ['beads']
daily: ['2026-03-23']
series: []
---

You can manually clone a dolt database from its git remote when `bd bootstrap` or `bd init` won't cooperate.

1. `bd dolt stop`: stop the server in the git repo you're restoring so you can operate on its database
2. `cd ~/.beads/shared-server/dolt`: go to the shared dolt server (it's `.beads/dolt/beads` otherwise, I think)
3. `rm -rf <prefix>`: remove the DB if it exists already
4. `dolt clone git+ssh://git@github.com/user/repo.git <prefix>`: clone it to your prefix
5. `cd - && bd ready`: see if you can see the listing

I don't know why my local just refused with `bd bootstrap` but this allowed me to fix it manually.
