---
authors: ['björn']
date: '2026-01-28T14:00:20+01:00'
lastmod: '2026-01-28T14:00:20+01:00'
location: Sweden
title: 'If n8n shows invalid date error it might be Because of missing timezone config'
tags: ['n8n']
daily: ['2026-01-28']
series: []
---
Set `GENERIC_TIMEZONE` for n8n or you'll get `ERROR: You specified an invalid date.` when you try to publish a time triggered workflow.

I had done a server migration and completely missed the `.env` file when copying, and [after recreating it](https://docs.n8n.io/hosting/installation/server-setups/docker-compose/#4-create-an-env-file) all started working.
