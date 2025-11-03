---
authors: ['björn']
date: '2025-11-03T14:59:25+01:00'
lastmod: '2025-11-03T14:59:25+01:00'
location: Sweden
title: Use `/@<name>` to access the value of an attribute when you've selected an element with XPath.
tags: []
daily: ['2025-11-03']
series: []
---
Use `/@<name>` to access the value of an attribute when you've selected an element with XPath.

With the expression `//*[@class="published-at"]` you will get the HTML tag that has `class="published-at"`, and if you then want the `datetime` property you add `/@datetime` to get it.
