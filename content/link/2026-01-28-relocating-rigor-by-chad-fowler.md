---
authors: ['björn']
date: '2026-01-28T12:30:45+01:00'
lastmod: '2026-01-28T12:30:45+01:00'
location: Sweden
title: 'Relocating Rigor by Chad Fowler'
tags: ['genie', 'testing']
daily: ['2026-01-28']
series: ['working-with-genies']
---
[Relocating Rigor](https://aicoding.leaflet.pub/3mbrvhyye4k2e) by Chad Fowler (via Muthu).

> Generative systems only work if invariants are explicit rather than implicit. Interfaces must be real contracts, not incidental boundaries. Evaluation must be ruthless. Failures must be loud and immediate. The engineer's job shifts from typing code to specifying intent and verifying outcomes.

This is very much how I'm currently thinking about working with AIs. I have been using genies to work in a legacy codebase (defined as no tests) I'm new to, and in a language and platform I have barely worked on, and I'm being useful.

I think it's because I decided to introduce tests to the codebase, verify the existing behavior for the flow I'm changing, and then write my new feature as a failing test. Then the genie has been able to iterate while I think about the changes and how they could fail.

For example, we had to move some columns into a new table, and while the code kept the `if null then 0` pattern that existed, I worried it might be overly "safe" and that it would return `0` because the relationship hadn't been loaded. So we traced through all the call sites to see that we also loaded that relationship from the DB, and the genie gave me a report I could follow and easily verify.
