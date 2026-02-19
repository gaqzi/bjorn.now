---
authors: ['björn']
date: '2026-02-19T09:58:42+01:00'
lastmod: '2026-02-19T09:58:42+01:00'
location: Sweden
title: 'Robby Russel - Most developers dont build new things'
tags:
  - engineering-culture
  - genie
daily: ['2026-02-19']
series: []
---

[Most developers don't build new things](https://robbyonrails.com/articles/2026/02/18/most-developers-dont-build-new-things/) by Robby Russell:

> We inherit. We understand. We stabilize. We extend. We improve what we can without destabilizing what already works.
>
> This kind of work rarely attracts attention. It looks like incremental improvement and steady compounding over time.
>
> But if most of your career is going to be spent in the second act, then the real question isn’t whether you get to start something new.
>
> It’s whether what you inherit gets better because you were there.

I fully agree with Robby, the big piece of what we do day-to-day is making sure we have a better tomorrow in the systems we're part of maintaining, and that's the lens we should be looking through.

For example, right now I've been working on an old system that's great at what it does and the business is happy with it, but it's not much fun to maintain. I have been using genies to help me and it's been a world of difference in how long it'll take to work on.

Yet, I spent a couple of hours yesterday manually verifying a long list of numbers to ensure we didn't break any calculations or displays in the workflow I have been changing. Because the system is a legacy one per Michael Feather's definition: it [didn't have any tests](https://understandlegacycode.com/blog/what-is-legacy-code-is-it-code-without-tests/) before I started working on it, and it's [my name on it]({{< relref "blog/2025-07-your-name-is-still-on-it.md" >}}), so as we're about to take it to production I need to do my best to ensure it will work and that the next person has an easier time. That's the work.
