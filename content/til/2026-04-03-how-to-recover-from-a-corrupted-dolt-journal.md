---
authors: ['björn']
date: '2026-04-03T13:17:06+02:00'
lastmod: '2026-04-03T13:17:06+02:00'
location: Sweden
full: true
title: 'How to recover from a corrupted dolt journal'
tags: ['beads', 'dolt']
daily: ['2026-04-03']
series: []
---

When dolt's journal is corrupted, `dolt fsck --revive-journal-with-data-loss` will truncate it back to the last valid record.

I found this error message when starting dolt up after upgrading the server: `invalid journal record at offset 5831169: invalid journal record: CRC checksum does not match`.

To recover, go to your dolt DB:

```bash
cd ~/.beads/shared-server/dolt/<db> \
  && dolt fsck --revive-journal-with-data-loss
```

It backs up the journal, truncates to the point it failed, and makes it possible to start the server again. In my case the db came back up with data loss. I did a `bd dolt pull` and it pulled in what I had pushed most recently, so nothing major was lost.

I'm guessing this happened because installing beads 1.0 also upgraded dolt. If you're upgrading, it's worth making sure you've done `bd vc commit && bd dolt push` in all repos beforehand. That means [configuring a git remote]({{< ref "/til/2026-03-20-configure-beads-dolt-to-share-via-git" >}}) first.
