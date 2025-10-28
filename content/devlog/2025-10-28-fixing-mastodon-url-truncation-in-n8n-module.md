---
authors: ['björn']
date: '2025-10-28T13:35:07+01:00'
lastmod: '2025-10-28T13:35:07+01:00'
location: Sweden
title: Fixing Mastodon URL truncation in n8n
tags:
  - n8n
  - genie
daily: ['2025-10-23']
series: ['working-with-genies']
---
I have been working on automating my [POSSE setup](https://indieweb.org/POSSE),
and ended up trying [n8n](https://n8n.io) and it has been a great experience,
there are so many plugins that it's mostly just wiring things together.

But, I discovered that despite being within the character limit,
one of my URLs were truncated when posting to Mastodon.
This is because Mastodon does something non-obvious: 
it treats all URLs as 23 characters, no matter if they're shorter or longer.

This is because they copied this behavior from Twitter,
which ran all links through their t.co link shortener.
The reason is that Mastodon doesn't want you to use a link shortener,
since it hides the real URL (i.e. makes rick rolling easier 😜).

So the module truncated the text in the status.
Since it wasn't URL-aware, all I got was a broken link.

I decided to fix it myself, because dammit, I'm a programmer.
It's an unfamiliar codebase I know nothing about, 
so I rolled up my sleeves and asked Claude, 
"_Pretty please, can you fix the problem and add tests?_"
(ah the modern world we live in)

The key constraint: I needed to understand every line of code before shipping it,
and it had to pass my quality standards because my [name would be on the PR.]({{< ref "blog/2025-07-your-name-is-still-on-it.md" >}})
Happily, that worked out [becuse my PR was accepted](https://github.com/redoracle/n8n-nodes-the-mastodon/pull/4). 🙂
   
Here's how I worked through it over three days. All [commits are here](https://github.com/gaqzi/n8n-nodes-the-mastodon/commits/url-aware-post-length-calculation/) if you want to step through them.
I really intend to share these devlogs earlier in the future, but I got lazy 😅

## The rough notes

Lightly edited for the web, and I've kept the day breaks in.

### 2025-10-08

I discovered that my mastodon poster truncated the URL (which seems to indicate that the n8n plugin does a naïve counting of characters, whereas it should only count 23 chars/URL, because Mastodon don't penalize longer URLs so we don't need link shorteners.

So I looked at the source for the package in question and found the 500 limit (I had looked at this before) and knew it was hardcoded, and then I decided to download the repo and ask Claude to find the bug and suggest a fix:

```plaintext {class="full-width no-copy-button"}
this is a plugin for n8n, and @nodes/Mastodon/status/StatusMethods.ts seems to have a bug where if I post a status with a link then it will truncate the status assuming the link takes up the full
length it has, instead of only 23 characters as is defined by Mastodon. Identify where this bug comes from, explain it, and come up with a plan for how to fix it. Also suggest tests to add that
fits with existing tests in this repostiory.
```

It then came up with a plan that I rejected because I wondered if there any existing packages that implement this logic, since the Javascript community is quite keen on tiny packages

<details>
<summary>The rejected plan to implement</summary>

```plaintext {class="full-width no-copy-button"}
Fix Plan

1. Create URL-aware character counting utilit

- Add new method ValidationUtils.calculateMastodonLength() that:
  - Detects URLs in the text using regex
  - Counts each URL as 23 characters (Mastodon's characters_reserved_per_url)
  - Counts remaining text normally
  - Returns the effective character count

2. Update validateStatusParam function

- Replace simple sanitizeStringParam with URL-aware validation
- Use the new calculateMastodonLength() to check if status exceeds 500 chars
- Only trim/reject if the effective length (with URL shortening) exceeds limit
- Keep the full URL text intact (don't truncate it)

3. Add comprehensive tests

Following the existing test pattern in __tests__/status.test.ts, add:
- Test for status with single URL that would exceed 500 chars without URL counting
- Test for status with multiple URLs
- Test for status with URL at the beginning, middle, and end
- Test that status correctly rejects when effective length > 500
- Test that long URLs are preserved in the request body
- Test edge cases: URL-like text that isn't a URL, localhost URLs, etc.

4. Optional enhancement

- Consider fetching instance configuration (characters_reserved_per_url) dynamically
- For now, hardcode 23 as it's the Mastodon standard
```
</details>

So I asked Claude to look for a package:
```plaintext {class="full-width no-copy-button"}
search and see if there's an existing npm package that does this calculation of post length per mastodon so we don't have to write it ourselves
```

It searched and didn't find anything (it was a bit slow, so I decided to look as well, and didn't find anything obvious), when I looked back after giving up it asked to download the original Ruby source for the [status length validation](https://github.com/mastodon/mastodon/blob/main/app/validators/status_length_validator.rb) and then came up with new search patterns

It then found twitter-text and suggested to import it and use
<details>
<summary>Plan to use twitter-text</summary>

```plaintext {class="full-witdh no-copy-button"}
Fix Plan for Mastodon URL Character Counting Bug

1. Add twitter-text dependency

- Run npm install twitter-text (version 3.1.0, stable and well-maintained)
- This library provides the same URL detection/counting logic that Mastodon uses

2. Update ValidationUtils in Mastodon_Methods.ts

- Add new method ValidationUtils.countMastodonLength(text: string): number
  - Use twitter-text's parseTweet() or extract URLs manually
  - Count each URL as 23 characters (Mastodon's standard)
  - Return effective character count
- Keep existing sanitizeStringParam for other use cases

3. Update validateStatusParam in StatusMethods.ts

- Replace line 16: Instead of truncating, validate the effective length
- If effective length > 500, throw error with helpful message
- Don't truncate the actual status text (preserve full URLs)

4. Add comprehensive tests to tests/status.test.ts

Following existing test patterns, add:
- Test: Status with long URL (>100 chars) that fits within 500 char limit
- Test: Status with multiple URLs counted correctly
- Test: Status that exceeds 500 chars even with URL shortening
- Test: URL preservation (ensure full URL is sent to API, not truncated)
- Test: Edge cases (URL at start/middle/end, multiple URLs)

This approach uses a proven library rather than reinventing URL detection regex.
```
</details>

I wasn't sure about all this because looking at the repo it looks like a big dependency, and maybe it has too much extra stuff that doesn't really come into play for Mastodon?

```plaintext {class="full-width no-copy-button"}
will `parseTweet()` introduce any other logic that might not work with mastodon? Might we be better off copying the code around links (and tests) and adding it to this repo (do the licenses match?)
We *cannot* break the existing behavior and throw an error instead of truncating, but we can change the truncating behavior to the effective length instead of actual length. 
```

It then went off and did a bunch of searches around east-asian specific character encodings (Japanese and Chinese alphabets as far as I can tell)

I then got a new plan that looks better, but I still wonder about the `when possible` for preserving URLs (I expect it is that if there's not 23 chars left, then it *has* to cut, so I will have it clarified in a more detailed plan)

<details>
<summary>The new plan that includes <code>when possible</code> for preserving URLs</summary>

```plaintext {class="full-width no-copy-button"}
Updated Fix Plan (Mastodon-Compatible)

1. Copy URL regex from twitter-text (with attribution)

- Add file header comment crediting twitter-text (Apache 2.0 license)
- Copy only the URL detection regex pattern (battle-tested, handles edge cases)
- No dependencies needed - just the regex

2. Create ValidationUtils.calculateMastodonLength() in Mastodon_Methods.ts

- Extract all URLs using the copied regex
- Replace each URL with 23-char placeholder ("x".repeat(23))
- Count remaining characters using standard .length
- Return the effective character count
- No CJK weighting - Mastodon treats all chars equally

3. Update validateStatusParam() in StatusMethods.ts

- Calculate effective length using new method
- If effective length > 500, truncate at boundary that fits within 500 effective chars
- Preserve full URLs when possible (don't cut URLs)
- Keep existing truncation behavior (no breaking changes)

4. Add tests to tests/status.test.ts

- Status with long URL (>100 chars) that fits in 500 effective chars
- Status with multiple URLs
- Status requiring truncation with URL preservation
- CJK characters counted same as Latin (no weighting)
- Edge cases: URL at boundaries, multiple URLs
```
</details>

I asked what `when possible` means and guessed some cases (I forgot to save the prompt)

<details>
<summary>The details for when it's not possible to save the URL</summary>

```plaintext {class="full-width no-copy-button"}
⏺ Cases Where We Cannot Preserve URLs:

1. Theoretical impossible case (highly unlikely in practice):

Text: "Check this out: https://example.com/article"
Actual length: 44 chars
Effective length (URL=23): 39 chars ✅ Fits!

But if someone tried:
Text: 480 chars of text + " https://example.com/very/long/url"
Actual: 520 chars
Effective: 480 + 23 = 503 chars ❌ Over limit!

To fit within 500 effective chars, we'd need to:
- Remove 3 chars from somewhere
- We can't split the URL (would break it)
- We'd have to remove text BEFORE the URL

2. Multiple URLs scenario:

Text: "See https://example1.com and https://example2.com and more text..."
If effective length > 500, we might need to:
- Keep URL1 (23 chars)
- Keep URL2 (23 chars)
- Truncate the "and more text..." part
- OR drop URL2 entirely if there's not enough room

3. The actual problematic case:

Text: 450 chars + "Visit https://example.com/some/long/url for more info and keep reading..."
Effective: 450 + 23 + 35 = 508 chars ❌

To fix:
- Keep first 450 chars ✅
- Keep URL (counts as 23) ✅
- Truncate "for more info and keep reading" to fit in remaining 27 effective chars

The Real Answer:

We can ALWAYS preserve URLs! Here's why:

- URLs only count as 23 chars in the effective length
- If someone has room for 23 effective chars, they have room for the full URL (even if it's 200 chars long)
- We just need to truncate the non-URL text to make room

The algorithm:
1. Find all URLs and their positions
2. Calculate effective length
3. If over 500:
  - Truncate text BETWEEN or AFTER URLs
  - Never truncate the URL itself
  - Work backwards to find a safe truncation point

Edge case that might force URL removal:
Text with 22 URLs: Each counts as 23 = 506 effective chars
Even with ZERO other text, we're over the limit!

In this case, we'd have to drop some URLs entirely (remove the last URL(s) until we fit).

Should I proceed with a plan that preserves URLs when possible, but drops trailing URLs if necessary when there are too many?
```
</details>

So, now to handle this I will ask it to write this high-level plan into `high-level.plan.md` and then to create a detailed plan that could be implemented by a junior engineer, so we then can ask sub agents to implement them step-by-step. I saw the plan and it suggested to drop URLs that went over the limit, so I asked it to instead keep them.

I haven't added any general/background context to this repo about my preferences, so I wonder if this will be enough to give me something useful in this repo:

```plaintext {class="full-width no-copy-button"}
create a deatiled implementation plan that a junior engineer could implement.

Ensure each step is written in a TDD fashion and that the tests are passing, changed to show the expected new behavior (red),
and then the change is implemented to make it pass (green).

Only implement as much as is needed to get each test passing and no more. 
Cover the copied code from Twitter with tests too.
```

It came up with a detailed plan, it looked good enough (skimmed it), so I asked claude to:

```plaintext {class="full-width no-copy-button"}
execute the test suite to verify it runs, if it runs successfully then document how to run the tests in the plan and then save the plan as plan.md
```

Then it couldn't run any commands, likely because I never ran `npm install` in the folder so I did that and verified that `npm test` worked and then asked Claude to try again.

Next up, execute the plan: `Now plan to execute @plan.md with subagents and marking off which steps has been done in the plan as they finish.`.

<details>
<summary>The plan</summary>

```plaintext {class="full-width no-copy-button"}
Strategy

Use general-purpose agents in parallel where possible to implement the plan steps efficiently. Track progress by updating plan.md with checkmarks as each step completes.

Phase 1: URL Extraction (Steps 1.1-1.6)

- Agent 1: Implement URL extraction utility with all tests
 - Create __tests__/url-extraction.test.ts
 - Add extractUrls() to ValidationUtils in Mastodon_Methods.ts
 - Iterate through all test cases in steps 1.1-1.6
 - Mark steps 1.1-1.6 complete in plan.md

Phase 2: Length Calculation (Steps 2.1-2.5)

- Agent 2: Implement Mastodon length calculation with all tests
 - Create __tests__/mastodon-length.test.ts
 - Add calculateMastodonLength() to ValidationUtils
 - Iterate through all test cases in steps 2.1-2.5
 - Mark steps 2.1-2.5 complete in plan.md

Phase 3: URL-Aware Truncation (Steps 3.1-3.9)

- Agent 3: Implement truncation with URL preservation
 - Create __tests__/url-truncation.test.ts
 - Add truncateWithUrlPreservation() to ValidationUtils
 - Iterate through all test cases in steps 3.1-3.9
 - Mark steps 3.1-3.9 complete in plan.md

Phase 4: Status Validation Update (Steps 4.1-4.4)

- Agent 4: Update status validation to use new utilities
 - Add tests to __tests__/status.test.ts
 - Update validateStatusParam in StatusMethods.ts
 - Verify all new tests pass
 - Mark steps 4.1-4.4 complete in plan.md

Phase 5: Final Verification (Step 5)

- Run npm test to verify all tests pass
- Update plan.md with final completion status
- Report summary of what was implemented
```
</details>

I then set Claude to execute and left some questions for myself to answer after we were done:

- Are there more places we should use this new validation/truncation logic?
- Is our new code implemented similarly to the rest of the code in this repository?
- What questions should I ask you to verify that we don't break something?

**00:34** It's late, so time to let Claude spin away while I prepare for sleep.

**00:50** Okay, while prepping for sleep it finished and I had a look on the new tests
the tests have some problems that we'll need to iterate on:

- Doesn't assert the exact values we're looking for
- Doesn't make the 500 or 23 constants and are instead magic numbers, let's name them
- The truncation logic is __too smart__ and it should just cut the URL and leave an ugly "scar" if that's what's required, that's fine. We can iterate on that

I think the way to work with this is to create a fork and do my changes in a repo with small focused commits, and then show the work as I commit, so I indicate how I grew the solution

Now, sleep for reals

### 2025-10-10
Okay, back at it again after a day's break, got some tunes on and now to review.

Okay, to help me document how I'm working on this I will [commit the change I got from Claude](https://github.com/gaqzi/n8n-nodes-the-mastodon/commit/8765c425b0cfffaf31d2b56ec00b4fa2dc855c72), and then I'll do my changes from there and commit as I do them.
Doing this so that it'll be easier to blog about it, and I don't know if that workflow will be what I want/need, so we'll see.

#### Reviewing
Starting the review by looking at the `status.test.ts` since I'm supposed to have good tests that tell me what's going on, so that'll be the lense through which I review this.

First off, I got header comments explaining the change that I don't need, so nixing 'em, and I think all these tests belong in a `describe` that shows that the tests belong together. [Commit](https://github.com/gaqzi/n8n-nodes-the-mastodon/commit/028b146d20234486eef241b63e9268e06d744a49)

Then, let's get going with the first test "should preserve long URL when using URL-aware character counting" doesn't do one that will hit the problem, and the test doesn't check the count is what we expect it to be (which is also a problem). okay, changed the test to __only contain__ a URL and then verify that the expected status is exactly 23 characters long, which passes. [Commit](https://github.com/gaqzi/n8n-nodes-the-mastodon/commit/f8500029bb7a2acae6763b1093501fb6ff681b67)

Next is a test with multiple long URLs, which is useful, make sure we don't do this for only one URL in the status. The URLs are not pushing it as far as it should, so I made both URLs more than the total length of a status `(80 -> 500)`
  ```javascript {class="no-copy-button"}
  const url1 = 'https://example.com/' + 'a'.repeat(80);
  const url2 = 'https://www.example.org/' + 'b'.repeat(80);
  ```

The `text` is a bit annoying so simplifying it for my own sake to make the length calculation simpler, it's a list of links one per line `(2*2+1 = 5 + 23 + 23 = 51)`:

```javascript{class="no-copy-button"}
const text = `- ${url1}\n- ${url2}`;
```
[Commit.](https://github.com/gaqzi/n8n-nodes-the-mastodon/commit/9a253678e5f4c4e8621a63c262374433c5f37ad4)

And about now I'm annoyed at the way the mock implementation has so much setup, it doesn't follow my coding style (too much repetition), but this isn't my project, and it seems to be how all other tests are written in this file so we keep it. **Consistency and avoiding surprises is more important than my personal style.**

Now comes the really nasty bit: Claude decided to **truncate text instead of URLs** which _isn't what I want_, if the URL is placed so that it's unavoidable that it will be cut, then cut it. Don't remove it, and don't remove text before it. It's better to indicate that something went wrong (by showing a cut URL) than silently dropping it
(I'd rather go boom than be silent, been saying this for a very looong time, mostly living that philosophy :p)

So I think this particular test will have to change. And about now I'm regretting that I didn't commit already because I feel I should've done it per test instead. Because now I'm about to make the test red, so I want to make sure I can change it cleanly. So, I'll undo my changes (thanks IntelliJ for having infinite undo in the same session), commit, and then redo per function.
That took ~5min to fix, and while not really necessary, I feel a lot better from going back and redoing and creating clean commits to show the work (so the commits linked was made before this).

Okay, now, this test I'll also change up a bit:

- Loong text, `a`x480, a space, and a url which means the effective length will be 505 so the URL will be cut
- I changed the assertion on the `sentStatus` to be the naively cut status instead (since the URL can't ever fit now, so it will just have to mangle the URL)
- And as expected, the test is now failing, so that's good. Now, let's ask Claude to fix the failing test I've created
- I highlighted the test in IntelliJ and opened up Claude and said (mostly because I haven't looked at the code, this might actually be faster to do manually, so I'll look at it as the fresh Claude session is figuring out what's going on):
    - ```plaintext {class="no-copy-button"}
      The highlighted test is failing correctly, I want to adjust the business logic to match. Confirm the test is failing by running `npm test` and then plan how to fix it 
      ```
Found the place where this is, it's in `nodes/Mastodon/Mastodon_Methods.ts` and the new `truncateWithUrlPreservation`.

And I see that Claude is spinning and reading what it's doing I realize I made a logical error: if Mastodon **always** counts URLs as 23 chars, **I can't truncate a URL and make it work.** The logic Claude made was reasonable since I told it to **never** raise an exception. So that means I need to make this case an explicit negative case, that it will fail the validation, and I could exemplify that **better** by making it a really short but valid URL (ex https://example.com which is 19 chars)

Okay, asked Claude to get to it, but it's struggling with the logic and I'm realizing that I should just add another test alongside this where we have a long URL at the start and a really long text at the end, that we can just truncate as needed, so it can see the logic better.

BUT, for right now, I'm gonna start a stew so I'll go do that and then let it… stew for a coupe of hours so I can continue then

**20:15** back and doing stuff again

I added another test that swaps the order so it's `<url> <text>` and now it's failing too, so let's clear the session for Claude and start over

```plaintext {class="full-width no-copy-button"}
these two tests are failing because the business logic is incorrect, suggest how we can fix the business logic
```

Claude came back with a plan to let the server fail instead of us truncating long tests, which won't make the tests pass, so I prompted:

```plaintext {class="full-width no-copy-button"}
before our changes this library truncated any text >500 chars, so we need to retain that logic. BUT if we end with a URL let it through and let the server
```

Claude then suggested a flow that seems to work:
```plaintext {class="full-width no-copy-button"}
New logic:
1. First check actual length (not effective length)
2. If text.length <= 500 → return text as-is (no truncation)
3. If text.length > 500:
  - Check if characters after position 500 are part of a URL
  - If yes (would break a URL) → return full text unchanged
  - If no (normal text overflow) → truncate at position 500

This preserves backward compatibility:
- Original behavior: truncate at 500 actual characters
- New behavior: same, BUT skip truncation if it would break a URL
```

And Claude implemented the fix and did it TDD style and highlighted that we have more code than necessary to pass, so I need to write another test case that exercises all the extra code we have in `truncateWithUrlPreservation`

## 2025-10-11

**14:43** The next day, I ended up watching TV yesterday, and today I'm feeling sluggish

But I was reflecting about this yesterday and I'm a bit unsure about how to write a test that refuses the current "fix" of " if the actual is less than 500 let through" because it's true since the edge-cases it won't do it for is basically where the URL is wrong, BUT, the URL could be wrong at the start and the text after is okay to be truncated. I.e. cases where say `https://example.com` (19) x 21 =  = 399 actual but the effective length is 483 and if I add 18 characters of text it'll fail and could be truncated.

Maybe that's the case to do, because it'll force it to handle it correctly.

I ended up changing the "this can be truncated" test so the URL is shorter and the text is exactly so it *should* pass, and then pointed out that we need to hint that we need the special logic if there are URLs in the text.

```plaintext {class="full-width no-copy-button"}
run the tests and suggest how to fix the them while not changing any tests, the underlying business logic is incorrect and too complex. Hint: consider only doing the special handling logic if there is a URL in the status text
```

Claude came back with a plan:

```plaintext {class="full-width no-copy-button"}
New simplified logic:

1. Extract URLs first to determine which path to take
2. If NO URLs in text:
  - Simple check: text.length <= 500 → return as-is
  - Otherwise → truncate at 500 actual characters
3. If HAS URLs in text:
  - Calculate effective length
  - If effective ≤ 500 → return as-is
  - If effective > 500:
      - Calculate how many actual characters to remove: excess = effective - 500
    - Target length: targetLength = text.length - excess
    - Check if truncating at targetLength would break a URL (cut it in half)
    - If YES (would break URL) → return full text unchanged (let Mastodon fail)
    - If NO (safe to truncate) → return text.slice(0, targetLength)
```

And that update gave me the logic I wanted, so now let's see what the change looks like and it's good.

As I now look at it and am preparing the commit message I realize, this doesn't fit the original design of this library/n8n node: it was blindly truncating, so I could also just truncate *just before* this URL so we can post. It doesn't __fit__ with how I discovered this problem, which was a truncated URL (which was still longer than 23 characters but wrong).

So, with that, I will instead say: nix the URL because it goes with the grain of the library and people like me have to ensure they truncate correctly. It's the least surprising thing we can do. But, I have done all this work and despite realizing that I went down the wrong path, I should commit what I got so I can see the changes. I learned something and that's still a win.

Okay, done , and I asked Claude to look at the comments I've tried to add to clarify the logic and it suggested some improvements to them which I've folded into the commit.

```plaintext {class="full-width no-copy-button"}
review the changes we've done, are the explanations in text clear enough that those reading the code would be able to understand?
```

[Committed.](https://github.com/gaqzi/n8n-nodes-the-mastodon/commit/5c311e2212bef9bbd5beb949d9e656c0ccba374a)

I'm not sure if using Claude here has saved me time, but I have been doing it in low energy and while watching TV, so upside is that it got done compared to that I likely wouldn't have put in the full energy otherwise. 

Although, partly that's because when fixing the bad stuff I didn't want to go in and learn how all the code worked, becasue I'm relying on the tests to tell me what's working and not, so that's pure laziness on my part. And the fact it dug through the full codebase and made a first pass when I was turning in for the night is _sooooo_ worth it. I'm sure I would've spent more time figuring out the codebase on my own otherwise.

But, I am also saying this _before_ I have manually tested any of this. I have only run the tests so far and not plugged it into n8n and seen if it works. So my optimism might still be premature.

Okay, updated one test file and the corresponding business logic, let's start with the next test file (which I changed a little for the previous task, so I know there's work to do).

### 2025-10-12

I did some final cleanup yesterday and didn't document it all, it's [only available in the commits](https://github.com/gaqzi/n8n-nodes-the-mastodon/commits/url-aware-post-length-calculation/), but I basically went over the changes as I would any PR at work and then raised it. The maintainer looked at it during the day and then [left a nice note](https://github.com/redoracle/n8n-nodes-the-mastodon/pull/4#issuecomment-3394429927) thanking me for being thorough and documenting my code well 🥰

> **Hey Björn!**
>
> Thank you so much for your outstanding contribution with PR #4! 🚀
>
> Your pull request to fix the URL character counting behavior was absolutely **fantastic** - it addressed a real problem that many users probably didn't even realize they were experiencing. The fact that Mastodon counts all URLs as exactly 23 characters regardless of their actual length is such an important detail, and your implementation handles it perfectly.
>
> ### What I especially appreciated about your work:
> ✨ **Thorough Research** - You referenced the actual Mastodon source code to validate the behavior  
> 🧪 **Comprehensive Testing** - 19 new tests covering all the edge cases!  
> 📚 **Excellent Documentation** - Clear comments explaining the "why" behind the logic  
> 🔧 **Smart Implementation** - The decision to remove entire URLs rather than break them is brilliant  
> 🔒 **Clean Integration** - Minimal changes to existing code while adding powerful functionality
>
> ### The Impact:
> Your fix means users won't have their URLs unexpectedly broken when posting longer content. That's a real quality-of-life improvement that will prevent confusion and frustration.
>
> ### Code Quality:
> The implementation is clean, well-tested, and follows all the best practices. It's the kind of contribution that makes maintaining open source projects a joy!
>
> **Would you be interested in contributing more to this project?** Your expertise with Mastodon's APIs and attention to detail would be incredibly valuable.
>
> Thanks again for taking the time to identify this issue, implement a robust solution, and provide such thorough testing. This is exactly the kind of contribution that makes the open source community amazing! 🙌
>
> Best regards

As they said, these interactions make open source fun because it's people working and building stuff together 🙂

