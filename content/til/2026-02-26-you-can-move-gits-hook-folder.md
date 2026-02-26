---
authors: ['björn']
date: '2026-02-26T14:35:58+01:00'
lastmod: '2026-02-26T14:35:58+01:00'
location: Sweden
full: false  # set to true if the full thing should be shown in listings
title: You don't have to symlink git hooks, move the hooks folder to your scripts
tags: ['git']
daily: ['2026-02-26']
series: []
---
Use `git config core.hooksPath script/hooks` and it'll use the scripts in `script/hooks` as hooks in the git project. Version controlled, and no need to update symlinks as scripts come and go.
<!--more-->

The way I have historically managed the hooks is by having a `script/bootstrap` that symlinks scripts, and then hopefully my team mates run bootstrap when something changes.

So this is a nice way of making that entire problem go away.
