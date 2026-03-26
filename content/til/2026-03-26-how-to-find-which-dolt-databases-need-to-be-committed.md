---
authors: ['björn']
date: '2026-03-26T15:32:42+01:00'
lastmod: '2026-03-26T15:32:42+01:00'
location: Sweden
full: true
title: 'How to find which dolt databases need to be committed'
tags: ['beads', 'dolt']
daily: ['2026-03-26']
series: []
---

dolt's shared server won't pull until all databases on the server have committed changes, not just the beads project you're pulling.

You'll get `Error 1105 (HY000): cannot merge with uncommitted changes` and it's confusing when the beads project you're working in has autocommit on. The uncommitted changes are in a different project that's also using the shared server.

The fix is to go through your other projects and commit their changes (or enable autocommit by adding `dolt.auto-commit: "on"` to `.beads/config.yml`). To find which databases have uncommitted changes:

```bash
query=$(bd sql "SHOW DATABASES" 2>/dev/null \
  | grep -v -E "^(Database|--|\(|dolt|information_schema|mysql)" \
  | while read db; do
      echo "SELECT '$db' as db, table_name, status FROM \`$db\`.dolt_status WHERE table_name != 'config'"
    done \
  | paste -sd'|' - | sed 's/|/ UNION ALL /g')
bd sql "$query"
```

For each project that shows up, go in and run `bd vc commit -m 'Snapshot'`, and then you can pull again.

We're ignoring changes to the `config` table because they don't seem to matter for pulling.
