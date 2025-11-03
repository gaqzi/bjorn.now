---
authors: ['björn']
date: '{{ .Date }}'
lastmod: '{{ .Date }}'
location: {{ .Site.Params.defaultLocation }}
draft: true
title: '{{ replace .File.ContentBaseName "-" " " | title }}'
subtitle: ''
tags: []
daily: ['{{ (time .Date).Format "2006-01-02" }}']
series: []
---
