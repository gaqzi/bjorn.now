---
authors: ['björn']
date: '2026-02-26T17:44:42+01:00'
lastmod: '2026-02-26T17:44:42+01:00'
location: Sweden
title: 'How Steve Yegge gets quality when vibing'
tags:
  - gas-town
  - genie
daily: ['2026-02-26']
series: ['working-with-genies']
---

I have been wondering how Steve Yegge gets quality when vibing and this seems to be how, from the emergency manual [Tending the Invisible Garden](https://steve-yegge.medium.com/gas-town-emergency-user-manual-cf0e4556d74b#7804):

> When you work with Gas Town, you don’t usually have time to inspect the code you’re creating. That’s not your role. But you need to make sure the code meets your quality bar. How do you ensure your garden is healthy if you can’t see it?
>
> The answer: **regular code review sweeps, followed by bug-fix sweeps** that fix the issues filed during the code-review sweeps. Gas Town excels at both of these. It can generate tons of work with a swarm (filing Beads as it finds problems) and then crank through tons of work with another swarm. You just keep doing this until the code reviews are just nitpicking, or the agents say the code is ready to ship. Do some of this every day, and hope that most of the time you don’t find anything bad. The only way to be sure is to do it all the time.
>
> Your garden can get diseases. I mentioned “heresies” above. Agents are very approximate workers and they like to guess at stuff. They will often make wrong guesses about how your system is supposed to work. If that wrong guess makes it into the code, sneaking through the review process, then it becomes enshrined and other agents may notice it and propagate the heresy in their own work.
>
> “Idle polecats” is an example of a heresy that plagues Gas Town. There is no such thing as an idle polecat; it’s not a pool, and they vanish when their work is done. But polecats do have long-term identities, so it’s more like they are clocking out and leaving the building between jobs, which is harder for agents to wrap their heads around. So “idle polecats” make it back into the code base, comments, and docs all the time.
>
> I’ve found the most helpful way to rid yourself of persistent heresies is to capture your guiding principles in the agent priming (onboarding). Which means you have to come up with some guiding principles in the first place.
>
> Your core principles or axioms will be different for every project you’re working on. But the more coverage you can get with them, the more classes of heresy you can avoid or easily correct simply by pointing at the principle they violate. Gas Town core principles include things like Zero Framework Cognition (shared with Beads), which I’ve written about, GUPP, MEOW, Discovery over Tracking, Beads as the Universal Data Plane, and so on. All of these help me stamp out heresies that try to creep into my code.

I've been guessing that philosophy/principles is the core piece, and that I need a good way of encoding so genies use 'em. I had already started iterating by creating a skill to review Go tests based on my [How to design a test suite you'll love to maintain](https://speakerdeck.com/gaqzi/how-to-design-a-test-suite-youll-love-to-maintain) and [Mocking your codebase without cursing it](https://speakerdeck.com/gaqzi/mocking-your-codebase-without-cursing-it) presentations, and I rarely have feedback to Claude on the tests anymore.

I still have plenty of disagreements on package design, naming, etc., and I haven't worked on encoding my preferences, or principles, into something reusable there. Luckily, I've been taking notes on what I've disagreed with the agent about, so it'll make it easier to start having the conversation to create the skill. When I have quota again.

Separately, I have been experimenting with Gas Town today, and it has chewed through my Claude Max 5x quota in an hour each time. I was warned, so I'm not complaining. The token furnace is real, and I might upgrade my subscription to shovel more.

Gas Town asked me to file a bug because it found a problem with beads (something about wisps?), so maybe that's why it has churned through the quota burn? Probably not.

Meanwhile, I'll start digging into how Steve has tried to encode his philosophies into Gas Town. Pilfering gloves on.
