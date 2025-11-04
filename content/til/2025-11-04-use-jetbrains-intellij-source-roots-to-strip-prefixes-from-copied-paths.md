---
authors: ['björn']
date: '2025-11-04T12:13:45+01:00'
lastmod: '2025-11-04T12:13:45+01:00'
location: Sweden
full: true
title: 'Use Jetbrains IntelliJ Source Roots to strip prefixes from copied paths'
tags: []
daily: ['2025-11-04']
series: []
image: /img/2025/11-intellij-copy-path.png
---
Marking the `content/` folder for your Hugo site as a "Source Root" in IntelliJ lets you use `Path from Source Root` to get the path to the file without the `content/` prefix you don't need when linking internally.

To make linking internally easier, I created [an Alfred app snippet]({{< relref "blog/2024-04-15-day-to-day-automation-using-alfred.md#text-replacement--snippets" >}}) (<code>{{\< relref "{clipboard}" >}}</code>), so now I only have to open the other post, double-tap shift, type "source root", then run the snippet, and all linked up.

{{< figure src="/img/2025/11-intellij-copy-path.png" caption="Right-click folder → Mark Directory as → Sources Root.<br>To copy path: open file and search 'source root', or right-click → Copy Path/Reference → Path from Source Root" alt="IntelliJ context menu showing Copy Path/Reference options with 'Path from Source Root' highlighted" >}}
