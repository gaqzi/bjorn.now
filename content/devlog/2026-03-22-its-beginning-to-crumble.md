---
authors: ['björn']
date: '2026-03-22T23:31:31+01:00'
lastmod: '2026-03-22T23:31:31+01:00'
location: Sweden
title: "It's beginning to crumble"
subtitle: 'The first steps of my breadcrumb tool'
tags: ['beads', 'genie']
daily: ['2026-03-22']
series: ['building-breadcrumb']
---
I had a breakthrough while working on [bjornstack](https://github.com/gaqzi/bjornstack) that made me realize how I could make an MVP of breadcrumb, the tool I've wanted to build for ~18 months.

So anyway, bjornstack is my opinionated take on how to write code, aimed at constraining and guiding genies to get their work done. And while working on it, like I have been whenever I'm working with genies, I got thoughts that I wanted to explore later, or ideas for other things I'm working on. I realized that since I started using beads capturing _in this project_ has gotten easier, while chatting I just mention we need "a new bead about x because y provide all the context we have here" and then there'd be a new bead linked to the work we were doing, and I can just pick it up later.

But as soon as it was something for another project, or even just "I need to remember to pack the charger when I leave the office today," then I had to break out to capture the thought, and blow my stack and lose my flow.
And if I don't capture it, I lose the thought.

<!--more-->

Somewhere on Saturday I realized this is how [Gas Town](https://github.com/steveyegge/gastown) seems to be using [beads](https://github.com/steveyegge/beads): You sling beads across projects, they get filed, and they can be queried across everything you're working on. There are ephemeral beads and long-lived ones. It's beads all the way down.

So maybe the breadcrumb app I've been thinking about, crumb for short,
doesn't need to be a custom database with all the trimmings.
Maybe, as a first version, it's just a thin wrapper around beads.
A skill I can give to an agent that says: this is how you record something into my breadcrumbs.

## What I've been missing

I've been thinking about building breadcrumb for a while now, and I was stuck on how to get started. The idea is simple, capture stuff when you realize it, but it's hard to do without breaking flow. I was thinking of doing it when committing because it's a point of "I'm done" but I'm not really committing as much anymore on my own now.

Back before I started doing a lot of my work in chat windows with _genies_ I would do the majority of my thinking in Roam Research. It was structured, it had bidirectional links, and I could find most things super easily. I had workflows to help me think. Glorious. ✨

But when I started building with agents, it would break me out of what I was doing to go leave breadcrumbs in Roam so I could track what I had been up to. So I stopped. And honestly, it was something I noticed when I worked on meaty problems when programming too, I would get caught up in what I did and not take notes. To my detriment later.

So, I wanted to get back to having my interstitial journal workflow I loved in Roam, to be able to look back on a day and get a feel for how it went based on the notes I left myself. And also have a better trail of things I learned as I worked.

And I also wanted to restart the strong weekly review routine I had, which was where I realized a lot of the stuff I did that turned out to be good ideas at work. I have also been reading Cal Newport and I wanted to start doing his daily shutdown routine, and the daily planning with a startup routine. So let's see if I can bake those into this too.

The thing I want crumb to be is kind of the flywheel that helps me grow. Daily capture feeds into daily reflection. Daily reflection feeds into weekly review. Weekly review is where I compound what I learned. The whole point is being able to retrace your steps. I did something, I learned something, and months later when I need it I can actually find it. 

And over time **the system starts producing things I actually care about**: a brag document that writes itself from the work I did (even as my own boss, it feels good to see how much I got done), TILs worth sharing, a personal solution database I can query when I hit a similar problem months later. I don't have to buy into "journaling is good for you" to get value, I just need to care about any one of those outputs.

## What I built

I knocked out a first version today.
It's a global Claude Code skill that I install on my machine.
In any session, in the middle of whatever I'm working on,
I just write `(crumb: <whatever thought I had>)` and it gets sent over to my cottage project. It can be anywhere in the prompt because I told it to look for either `/crumb …` or `(crumb:…)` and it just worked.

One thing I learned getting this to work:
the skill needs to `cd` into the cottage project directory and run beads from there when creating.
Otherwise beads doesn't know which project context to file things into.

So I made a small wrapper around `bd` (the beads CLI) that I could [allowlist globally]({{< relref "til/2026-01-10-claude-code-sandbox-exclusion-requires-both-permissions-allow-and-sandbox-excludedcommands.md" >}}) in my Claude Code settings:

```sh {class="no-copy-button"}
#!/bin/sh
# Wrapper that runs bd against the cottage project database.
# Works from any working directory.
cd "$HOME/workspace/cottage" && exec bd "$@"
```

The key ideas:

- It finds a daily journal bead in the cottage project (or falls back to creating a plain bead)
- It captures provenance: which project you're in, which bead you're working on, so you can backtrack to it later if you want more context
- It files the thought as a comment on the daily bead, then moves on, and the nice part of the comment is that it gives me _when_, a timestamp, and it doesn't matter if I'm working on several repos at the same time because it'll just be combined anyway in the daily bead.

<details>
<summary>The full crumb skill</summary>

````plain text {class="full-width"}
---
name: crumb
description: "Quick thought capture — adds a comment to the user's daily journal bead in their cottage project. Trigger when the user says /crumb, 'crumb:', or uses the inline form '(crumb:…)' as a parenthetical aside. File the crumb FIRST before handling anything else in the prompt. The user is in flow; receive, file, move on."
---

# Crumb — Quick Thought Capture

## How to run commands

This skill includes a wrapper script `crumb-bd` that runs `bd` against the cottage database regardless of your current working directory. Use it for all cottage operations. Resolve the path relative to this skill's base directory:

```bash
scripts/crumb-bd <bd args...>
```

Every invocation needs `dangerouslyDisableSandbox: true` (Dolt needs raw TCP to localhost:3308).

**If any command fails, you MUST show the error to the user and echo back the crumb text so nothing is lost.** Don't silently swallow failures.

## Priority

File the crumb BEFORE responding to anything else in the user's message. The crumb is a side-channel capture — handle it first, confirm in one line, then continue with the main conversation.

## What this does

Adds the user's thought as a comment on their daily journal bead (a bead in the cottage project with label `daily`). The thought gets processed later during review — your job is just to file it.

## Parse the input

Format is `category: text` where the category is optional.

```
/crumb idea: what if protocols were composable
/crumb friction: dolt keeps dying on me
/crumb just a raw thought with no category
(crumb:reminder: pack the charger before leaving)
(crumb:idea: what if we split beads by domain)
```

Categories are freeform — `idea`, `friction`, `reminder`, `meeting`, `learning`, `question`, `todo`, whatever the user wrote. Don't rename or recategorize. No category is fine. `(crumb:idea: blah)` is valid — the category is `idea`.

## Find the daily bead

```bash
scripts/crumb-bd query "label=daily AND status=in_progress" --json
```

**Found:** Use it.

**Not found — fallback chain:**

1. Most recent closed daily that hasn't been reviewed yet:
   ```bash
   scripts/crumb-bd sql "SELECT i.id, i.title FROM issues i JOIN labels l ON i.id = l.issue_id WHERE l.label = 'daily' AND i.status = 'closed' AND i.id NOT IN (SELECT l2.issue_id FROM labels l2 WHERE l2.label = 'reviewed:daily') ORDER BY i.created_at DESC LIMIT 1"
   ```
   Comments on closed beads work fine.

2. No daily bead at all — create a standalone bead:
   ```bash
   scripts/crumb-bd create "<the thought>" --type task --priority 3
   ```
   Tell the user: "No daily bead open — filed as standalone bead."

## Build the comment

### Provenance

Capture where the thought came from — project name, and what the user was working on.

**Project name:**
```bash
basename "$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
```

**Active bead:** Use this escalation — stop at the first that works:

1. **Session context:** If the conversation has claimed or discussed a bead, use its ID and title directly.
2. **Query local db:** `bd list --status=in_progress --json 2>/dev/null` — use ID and title if exactly one result. Multiple results → pick the most recently discussed, or ask briefly. Zero → no active bead.
3. **Folder fallback:** If no bead is found and no beads db exists, record the working directory path. This lets the user query session logs for that folder and time later.

**Format the comment** with a provenance header on its own line, then the content:

```
(from bjornstack, bs-xyz — Refactor auth middleware)
idea: what if protocols were composable
```

When working in cottage, still include provenance if you're working on a specific bead — the point is capturing something different from current focus:

```
(working on in-mlk — Create the /crumb skill)
idea: what if we made categories queryable
```

If no bead is found and no beads db exists, use the working directory:

```
(from ~/workspace/some-project)
idea: what if protocols were composable
```

### Multiple thoughts

If the user drops several thoughts in one message, file them as a single comment separated by newlines. One provenance header, multiple entries:

```
(from bjornstack, bs-xyz — Refactor auth middleware)
idea: what if protocols were composable
friction: dolt server died again
reminder: pack the charger
```

## Add the comment

```bash
scripts/crumb-bd comments add <daily-id> "<the comment text>"
```

**If this fails:** Show the error AND echo the full crumb text back to the user so they can capture it another way. Example:

```
Failed to file crumb (connection refused). Your crumb text:
> idea: what if protocols were composable
```

## Confirm and move on

One line. The user is in flow.

```
Crumb filed → idea: what if protocols were composable
```

Multiple:
```
Filed 3 crumbs on <daily-id>
```

Don't engage with the content. If the thought is so terse that future-them won't understand it, ask for one line of context in the same breath — "Filed. Quick — what's the context? Won't make sense later without it." — then move on regardless.

## When to create a bead instead

Only if the user explicitly asks: "make this a bead", "track this", "this needs its own issue", or "bead: ...".

```bash
scripts/crumb-bd create "<thought>" \
  --description "Captured from <project>, working on <bead-id> — <bead-title>" \
  --type task --priority 3
```
````
</details>

The provenance bit is what makes this useful later.
When I'm doing my shutdown review, each crumb tells me where I was and what I was doing when the thought hit.
I don't have to reconstruct context, it's already there.

And it felt really nifty when I ended the day and the shutdown routine showed me: these are the beads you closed today, and here's the note you left yourself when you finished that session. A mini-review of my own work that I barely had to think about capturing. Because the majority of my work is already flowing through beads, it all just becomes queryable. It doesn't matter if I was working across several repos at the same time, the daily bead combines it all.

## Why beads and not something custom

When I was thinking about building this tooling,
I assumed I'd have to build something tool-agnostic (Roam/Obsidian/Apple Notes/etc),
and because this stuff is so sensitive, local-first with no centralized server.
By adopting beads and dolt, I get all of that for free.
Dolt pushes all the data into git, and there's an existing nice CLI interface, and more people are building on top of beads already.

I'm admittedly kind of abusing beads here.
It's not really designed for this kind of journaling.
But most of what I'm capturing are tasks I did,
and having a daily bead where I add notes as the day progresses,
that's kind of how research tasks work anyway.
You add comments, you talk to people, you figure it out,
and then it becomes a written conclusion.
So yeah, maybe bending it a little, but it's solving a whole lot more than it's bending.

A lot of the things I was originally planning to build already kind of exist,
just in a packaging that isn't necessarily optimal for what I want right now.
But it's a hell of a good start that I can adjust and adapt as I learn more about how I want this to work. And then get started on the part of "how do I extract more knowledge from all the information I'm creating?"

## What's next

I'm going to try this out for a bit and see how the daily and weekly routines feel.
If you're reading this and interested in trying it out before I share it publicly,
[send me an email](mailto:ba@bjorn.now?subject=Got some crumbs for me?) and I'll give you a preview.
