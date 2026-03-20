---
authors: ['björn']
date: '2026-03-20T12:50:24+01:00'
lastmod: '2026-03-20T12:50:24+01:00'
location: Sweden
full: true
title: 'How to migrate beads from per-project to shared dolt server'
tags: ['beads', 'dolt']
daily: ['2026-03-20']
series: []
---

To switch beads from a per-project dolt server to the shared server, do a backup, configure shared-server, and restore.

I was running in "a server per repo" mode and it's just unnecessary, they clash in annoying ways when switching repos, and once I understood how [beads store data in git]({{< relref "2026-03-20-configure-beads-dolt-to-share-via-git.md" >}}) I embraced dolt and the shared server. I had hesitated because I had somehow connected it with DoltHub, and that's optional for using beads.

1. `bd backup`: make sure you have your local database available for restore
2. `bd dolt stop`: so we don't conflict on anything
3. `bd dolt set shared-server true`: to configure this project to use the shared server
4. `bd restore`: to restore the db

For most of my projects this just worked, but in some cases I had to [reset the dolt configuration for the repo]({{< relref "2026-03-20-how-to-reset-beads-dolt-database.md" >}}).
