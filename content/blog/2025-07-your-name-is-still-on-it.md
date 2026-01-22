---
authors: ['björn']
date: '2025-07-24T23:00:00+08:00'
lastmod: '2025-07-24T23:00:00+08:00'
location: Singapore
title: Your name is still on it
subtitle: learning to ride the AI motorcycle without crashing
tags:
  - thinking-out-loud
  - ai
  - genie
  - which-role
  - kent-beck
series: ['learning-with-genies']
---
A colleague recently said something that's been rattling around in my head: "AI gives you speed, but it doesn't give you direction." And the more I use these tools, the more I think that undersells the danger.

I have been wondering how to think about AIs (or [genies](https://newsletter.pragmaticengineer.com/p/tdd-ai-agents-and-coding-with-kent)) and how [computers are like bicycles for the mind](https://medium.learningbyshipping.com/bicycle-121262546097), as Steve Jobs put it, and I think these tools take it further. They are more like motorcycles for the mind. They go _really_ fast, and you better not treat them like a bike, because you need to know what you're doing. How to handle that thing. You need to make sure you don't try to go too fast too soon, or for too long, because you'll get speed blind and… things will happen.

I'm pretty sure motorcycle insurance costs way more when you're in your 20s than in your 40s or 50s. There's a reason for that. People who are older generally know how to ride the thing, and they're not as wild when doing it.

But I think when it comes to using AI we're all kind of in our 20s because we're figuring it out.

## It's my name on whatever goes out

I was at a wedding recently, talking to this lawyer, 50s, 60s maybe, working at a multinational. He's been playing around with AI and feels it's giving him an enormous productivity boost for writing and doing research for him.

As we were talking about how he was using it he said something that stopped me cold: _"It's my name on whatever goes out."_

He's already caught the AI making things up. He has to check every line, every reference. He explicitly asks it to give him the references so he can look them up himself. And if I understood correctly, this isn't significantly different from when juniors do the work for him. Because it was still his name on it. He needs to validate it. Whatever he puts his name on and sends out has to be right.

And that's when something clicked for me. [Remember how I was talking about the different hats we wear?][which-hat] Well, you _can_ outsource wearing the hat. You _can_ have the genie do the work. But it's still your name on it. No one else cares if you outsourced it, they only see your name on it. You can't blame the genie for a shit job. It was your name.

## What we think we're automating

I keep hearing engineers say, "_oh, I don't have to do this boring thing anymore!_"

Meeting notes are a perfect example. I have access to Google Gemini at work, and people just let Gemini take meeting notes and send them out without reading them. Really. "_Huh?_" I hear some of you say now, that's what it's great for, the notes are [just toil](https://sre.google/sre-book/eliminating-toil/). Well, no, what are meeting notes actually for? They're about making sure we're on the same page, that we have the same agreements and understanding. If you let the machine mindlessly capture words and don't check that it actually documented the meaning behind what we said and understood, you're failing at the actual job of [running that meeting.]({{< relref "2025-05-03-effective-meetings.md" >}})

This reminds me of [Chesterton's Fence](https://fs.blog/chestertons-fence/), that principle about not removing a fence until you understand why it was put there. Before you automate away some "boring, pointless thing," maybe ask yourself: why is it that I'm doing this in the first place? Because if you don't understand why it's done, how do you know the automation did it well?

And I wonder if what's really happening is that we're not automating the work, we're automating away our attention to the work. We're not automating the output. We're automating away our understanding of what that output should be. And [experienced people are the ones who spot strange patterns (or have taste)](https://www.benkuhn.net/impact/) precisely because they've stayed engaged with the work over time. You can't develop that instinct if you're not looking.

## The work worth doing

Which brings me to [something eyebrow raising](https://tidyfirst.substack.com/p/90-of-my-skills-are-now-worth-0) that Kent Beck said: with AI, 90% of his skills became worthless, but the leverage of the remaining 10% is now worth 1000x. The question is: which 10%? This is the "_knowing where to put the X_" skill, [that judgment call and experience][which-hat-4999] you bring: that's what makes the genie do what's needed.

When you let the genie write code for you and it introduces bugs that you would have caught if you'd actually read the code… you're not doing your job as a product engineer. Yeah, you're slinging more code and doing it faster. But it's not about the code, it's about delivering the solutions we need when we need them.

There's a difference between _delegating execution_ and _delegating responsibility_. You _can_ have the genie execute tasks, but you _can't_ delegate the responsibility for the outcome. That's still yours. [The hat][which-hat] is still on your head, even if AI is helping you get things done faster while wearing it.

And I find pride in doing the work well. Even the boring bits. Sometimes we might not enjoy the work, but doing things well will make most things feel worthwhile. Because there's nuance and understanding you can only get by truly groking something, and that's when you can safely change and improve it.

[which-hat]: {{< relref "2025-07-which-hats-are-you-wearing.md" >}}
[which-hat-4999]: {{< relref "2025-07-which-hats-are-you-wearing.md#the-9999-skill" >}}

## Finding your balance

The question isn't "can the genie do this task?" It's "when it does this task and puts my name on it, am I comfortable with what might happen if it gets it really, really wrong?"

In my experience, the engineers who are using AI most effectively are the ones who treat it like that lawyer treats it: as a powerful tool that still requires their full professional judgment. They understand they're being paid for the judgment part of the work, not just the execution part. The genie can help with execution, it can draw lots of Xs quickly. But knowing where to draw them? That's all you.

Right now, these systems can't truly understand context the way a senior does. They can't make actual judgment calls, they're pattern matching (even if, admittedly, [slightly magical](https://en.wikipedia.org/wiki/Clarke%27s_three_laws) in how they do it). They give us speed, not judgment or direction. Output, not understanding.

I'm still working out what learning looks like when AI can show you all the moves. My cooking has genuinely leveled up with an AI coach: I'm making dishes I never could before, and understanding why certain techniques work. But I know this is like training wheels. I couldn't fully do this alone yet, and that's the thing: I'm not mistaking this _speed_ for actual _skill_, not confusing making _progress_ with real _proficiency_.

So here I am, learning to ride this thing safely, trying to get out of my AI twenties you might say, before I take it on the highway.

Because whether you're wearing your engineering hat, your architect hat, or your team lead hat, your name is still on it. And I'd like to make sure I am not only wearing the helmet but also know how to ride this motorcycle before I really open up the throttle.
