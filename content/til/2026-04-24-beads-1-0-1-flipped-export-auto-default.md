---
authors: ['björn']
date: '2026-04-24T19:43:23+02:00'
lastmod: '2026-04-24T19:43:23+02:00'
location: Sweden
full: true
title: 'beads 1.0.1 silently starts exporting issues.jsonl by default'
tags: ['beads']
daily: ['2026-04-24']
series: []
---
beads 1.0.1 [flipped the `export.auto` default to on](https://github.com/gastownhall/beads/commit/64e504d5#diff-8bba7fff92456c4a9bd807232acd9b5eaf6491c2249600c587d4da4b1ba50492R43), so old projects silently start exporting `issues.jsonl` after upgrade. To opt back out, run:

```shell
bd config set export.auto false
```

New projects [get prompted during init](https://github.com/gastownhall/beads/commit/64e504d5#diff-7d79935b4facccae363f0f50884254beb035cc02d5289a795d2181d31e4f20efR1638), only existing projects will get this nice surprise.

If you're using [dolt's git export]({{< ref "/til/2026-03-20-configure-beads-dolt-to-share-via-git" >}}) instead, commit the config change and delete the `issues.jsonl` file.
