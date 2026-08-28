---
authors: ['björn']
date: '2026-08-28T23:13:35+02:00'
lastmod: '2026-08-28T23:13:35+02:00'
location: Sweden
full: true
title: "The IKEA Kajplats bulb wouldn't pair because my network had no IPv6"
tags: ['how-to', 'home-automation']
daily: ['2026-08-28']
series: []
---
[Matter](https://en.wikipedia.org/wiki/Matter_(standard)) over [Thread](https://en.wikipedia.org/wiki/Thread_(network_protocol)) requires IPv6 on your local network, so if you can't pair the [IKEA Kajplats bulb](https://www.ikea.com/nl/en/customer-service/product-support/smart-lighting/smart-lighting-support-pubd8491250/#3eed3150-08de-11f1-90c3-d5e60346fe38) that might be why.

I didn't have IPv6 enabled, and my ISP doesn't assign IPv6, so I used [unique-local-ipv6.com](https://unique-local-ipv6.com/) to get a unique prefix. Configured it as `static` in my local network setup, alongside the IPv4 configuration, on my UniFi Dream Machine and then all my bulbs connected.

Now my niece is learning to pronounce English colors as she cycles my apartment through every shade of the rainbow 😁
