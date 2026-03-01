---
authors: ['björn']
date: '2026-03-01T22:06:44+01:00'
lastmod: '2026-03-01T22:06:44+01:00'
location: Sweden
full: false  # set to true if the full thing should be shown in listings
title: 'git rm --cached <file> will remove from git but not from the filesystem'
tags: ['git']
daily: ['2026-03-01']
series: []
---
`git rm --cached <file>` will remove a file from git's tracking but leave it on the filesystem. Great if you accidentally commit something that should've been in `.gitignore`.
