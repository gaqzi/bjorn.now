---
authors: ['björn']
date: '2026-03-20T11:29:14+01:00'
lastmod: '2026-03-20T11:29:14+01:00'
location: Sweden
full: false  # set to true if the full thing should be shown in listings
title: "How to reset beads' dolt database"
tags: ['beads']
daily: ['2026-03-20']
series: []
---

When [beads](https://github.com/steveyegge/beads) can't find or create a [dolt](https://github.com/dolthub/dolt) database, delete the local dolt state and reinit.

The errors look like this:

```text
Error: failed to open Dolt store: database "bs" not available after CREATE DATABASE: Error 1049 (HY000): database not found: bs
```

or:

```text
Error: failed to open database: database "bs" not found on Dolt server at 127.0.0.1:3308
```

<!--more-->

Fix it by stopping dolt and removing its local state:

```shell
bd dolt stop  # or you won't be able to delete all the files
rm -rf .beads/dolt/
rm .beads/dolt-server.*
```

Also check `.beads/metadata.json` for stale server connection config. Mine had extra fields that were messing things up. I cleaned it down to just the essentials:

```json
{
  "database": "dolt",
  "backend": "dolt",
  "dolt_mode": "server",
  "dolt_database": "bs",
  "project_id": "deadbeef-9164-426d-8c1c-ff8ae5d35e3e"
}
```

Then reinit: `bd init --force --prefix <yourprefix>`.

`bd doctor --fix` couldn't sort this out, which is why I ended up doing all this manual cleanup.

I hit this upgrading to beads 0.61.0 when switching to shared-server mode.
