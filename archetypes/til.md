---
authors: ['björn']
date: '{{ .Date }}'
lastmod: '{{ .Date }}'
title: '{{ replace .File.ContentBaseName "-" " " | title }}'
tags: []
daily: ['{{ (time .Date).Format "2006-01-02" }}']
---
