---
authors: ['björn']
date: '2025-11-03T15:04:43+01:00'
lastmod: '2025-11-03T15:04:43+01:00'
location: Sweden
title: 'Maintaining n8n inline Javascript as code'
subtitle: '…and more importantly: with unit tests'
tags:
  - n8n
daily: ['2025-11-03']
series: []
---
In this devlog I'll make a change in my n8n POSSE setup,
that could've taken ~an hour if I kept doing it manually as I had,
but instead I spent ~5 hours tidying and removing manual steps for the future.

The work itself was about making my "scraps," that is this site's tweets,
be sent out raw to my syndication targets.
I feel that sending a link to something you see in the preview,
or it could be inline in the post, is a bit much,
I should just let it show up in the platform itself.

I have a couple of things planned for this site,
and this was chosen as the first step
because it would force me to think about _how will I maintain_ my n8n workflows.

So now, instead of writing some Javascript code, thinking really hard,
and then test it by tooting something out, I instead have some unit tests and
a way to programmatically update my workflow. So as I go down the rest of my
list of tasks I want to do working with n8n will be much smoother.

I had a couple of decisions to make,
so I listed them out using the [Choice algorithm of thought](https://www.cortexfutura.com/getting-started-algorithms-of-thought/#simple-choice-algorithm),
and as always it forced me to dig deeper into the problem,
even if I ended up doing what I guessed going in. 
But, the benefit of this process is being intentional and explicit, it
gets me into the mode of "I'm trying to list out options," and to explain
what made me make the decision. Since this is now recorded in my notes
I can easily go back later to find why.

The kind of highlights of what I got done:

- [Updating n8n programmatically](#updating-n8n-programmatically):
  Extract the code from a Javascript source file (glorified `grep`),
  and then wrap it so it'll work in n8n.
- [Creating reusable tests in Javascript](#implementing-reusable-tests):
  which turned out to be a bad idea, because the code was the same but
  diverged too much, so keeping the tests the same would've needed too much
  conditional logic.  
  So I ended up copy/pasting instead of creating a maintenance nightmare.
  This pattern is useful to know, though, I use it in other codebases where
  the code is duplicated but some shared logic needs to stay the same.
  For example, adapters for databases implementing a common interface.
- [Telegram Instant Views](#update-telegram-logic): Learning about and configuring.
  Create an Instant View template for this site and learn a bit more about XPath.
- [n8n's update API](#understand-how-n8n-updates-work):
  Dig into what logic there is calling the update workflow REST endpoint, 
  so I understand what I might break with how I decided to perform updates.
  Created a guard-rail to try and catch if I'm about to overwrite click-ops
  changes I hadn't accounted for when changing locally.

{{< toc >}}

## Background and scope of work

I will (for now) not add images to scraps until I have native support for images in my posting (so they either only exist in a special content type, which gets linked, or they're attached when posting as a scrap).

I do this because I feel linking to these short-text things that really could just live on Masto/Bsky/etc. is a bit much, be a bit more native to them. Do use them to publish my other content but don't only send links when they're not necessary. It feels like being a bad citizen to them when it's only a sink that way.

The way I've setup the sending in n8n right now, is that I have two steps in the status: 1) truncating the body and deciding if we need more, 2) and then adding the link, so I need to figure out a better maintenance pattern.

- **Choice:** Manage n8n workflow with source management
  - **Constraints:**
    - Be able to recreate my n8n setup if something goes belly-up
    - Keep as much as possible in source (but don't overdo it, I'm a single person doing this and can manage myself)
  - **Options:**
    - Keep n8n fully clickops and keep code snippets in blog
      - **Advantages:**
        - Super simple and what I'm doing, the status quo choice
      - **Disadvantages:**
        - If I have to recreate the n8n setup from scratch, painful
    - Create the workflow file in my blog and upload it for changes
      - **Advantages:**
        - All my n8n stuff is in my blog, so it's easy for me to deal with, and it's something I can easily share later so that's a win for sharing
      - **Disadvantages:**
        - More work to figure it out right now
          - But probably worth it, I'll download the workflow file and look at it to see what it says
          - looking at the JSON file it looks pretty straightforward, and using JQ I should be able to pretty easily inject what I need into it, so I can create a small file/script to help me out here that'll be worth it I think
  - **Decision:** Create the workflow file in my blog and upload it for changes
    - It feels like a good step towards a maintainable setup and minimal effort to get it going

Doing the choice here wasn't necessarily super useful, I kinda knew that I wanted to start storing the workflow in my repo, but the point was to step back and consider what I was doing. I was in my head starting to go down the path of just doing what I have been doing, it has been fine. But when I decided to look at the options "the engineer in me" reeled back enough that I felt that this time investment _will_ be worth it.

Okay, the following jq will let me update a specific field in my workflow file, so I will have to make it do it "in context", so that's a good start for what I'm doing.

```plaintext
jq '.nodes[] | select(.id == "e1bd320b-1222-4324-9168-22372d2e667c") | .parameters.status |= "m000"' src/n8n/bjorn.now-feed-distribution.json
```

So I think I want my maintenance to be: full status to be handled in one javascript block, so I can extract that and use jq to update the json file.

I haven't decided how I will ensure the javascript and json are up to date, maybe I'll just do a makefile because it's easy for now? Or maybe I do a template that doesn't store the "production data" so that I never have the actual prod version checked in and only create it on the fly as I'm updating to encourage avoiding the disconnect.
I'll decide later.

## Coding the Mastodon logic

With a short lunch break I'm now back at it, so let's start by creating the logic I want so that I can let JQ pick it up.

### Designing the solution

Worry: I'm not sure exactly _how_ I will inject this into JQ right now, will I do a full JS file? Extract it smarter and use JQ as a library since I anyway has setup Javascript in the blog…? I don't know, I'll look into that AFTER I have finished updating the code I want and verified it manually, then I'll do this.

Okay, so what do I have available in the current setup?

I get injected `$('RSS Feed Trigger').item` into my inline function, which contains all the information from the RSS feed, so that's perfect, that means I don't need to send in anything more, I just need to decide what to output.

To make my testing life a bit easier I will now go and take my test data and make that available in a test, so I can TDD this thing.

Looking at [my code that I've used in mastodon](https://github.com/gaqzi/bjorn.now/blob/df4abc0a299906a8c357a6e4619ce01ab5d4c530/src/js/n8n.copies.js#L7-L31) (I just remove the `let mastodon = ` when using) I think it'll work well as-is, so let's start by backfilling some missing tests, so I have a clean place to work from, the only problem is that I'm calling it as I should in mastodon because I was only using it manually, so that'll have to go.
For now, I'll remove the self-calling and figure out how to deal with this when I inject with jq, since it feels like as long as I can get the function definition I can very easily wrap it in a self-call with the param I need.

### Backfilling tests for the existing code

```javascript
let mastodon = ((item) => {
    let msg = item.json.contentSnippet,
        msgLength = 500-23-1, // the default mastodon post size is 500, -23 chars for the link, and -1 char for newline
        isTruncated = item.json['content:encodedSnippet'] !== item.json.contentSnippet,
        truncateIndicator = '\n… more';
    let wordTruncate = (str, n, indicator) => {
        if (indicator === undefined) indicator = '…';
        if(str.length <= n) return str.trimEnd();
        n -= indicator.length;
        if(str[n] === ' ') return str.substring(0, n).trimEnd();
        let ret = str.substring(0, n).trimEnd(),
            i = ret.lastIndexOf(' ');
        // when there's no spaces at all, just cut in the middle of the text.
        if (i === -1) return ret.substring(0, n);
        return ret.substring(0, i).trimEnd();
    }
    msg = wordTruncate(msg, msgLength, truncateIndicator);
    return isTruncated ? msg + truncateIndicator : msg;
})($('RSS Feed Trigger').item)
```

Cool, I have a first test showing the standard behavior of not including any links, so let's continue backfilling everything and then I'll add in the rest.

That was only two tests, nothing much to write home about but this covers the behavior I have and it's enough to characterize it for me, so these are the changes I want to do now:

Output the link as well, on a newline of it's own.

### Implementing the new logic

So I'll do this first, and make sure it's done correctly for both tests, I will start by making both tests fail, because that feels like the best way.

If the URL contains `/scrap/` then only output link if truncated.

Done, the code is there, I have some tests, it's nothing too spectacular, but it does what I want.
I realize that I should install standard and run the formatter regularly because I'm being inconsistent and I don't like it. `gofmt` and `black` has ruined me 😁.

## Updating n8n programmatically

Now to figure out how to merge this into my workflow file.

- **Choice:** How to merge my javascript into my workflow file
  - **Constraints:**
    - No manual steps
    - Need to return the function to run, and then transform it into a "self-run" (`((item) => { item.json.link })($('RSS Feed Trigger').item)`) so it'll work
  - **Options:**
    - Is there some easy AST stuff I can use with node to extract it?
      - Let's ask claude
        - ```plaintext
          is there a function in node to parse the AST of a javascript file and to get the content of a variable as a string?
          ```
      - **Advantages:**
        - Exists, will be robust
          - I got back a code example but I'm hesitant to pull in these dependencies
            - ```javascript
              const parser = require('@babel/parser');
              const traverse = require('@babel/traverse').default;
              const generate = require('@babel/generator').default;
              const fs = require('fs');
              const code = fs.readFileSync('functions/processData.js', 'utf8');
              const ast = parser.parse(code, { sourceType: 'module' });
              let functionCode = null;
              traverse(ast, {
                FunctionDeclaration(path) {
                  if (path.node.id.name === 'processData') {
                    functionCode = generate(path.node).code;
                  }
                },
                VariableDeclarator(path) {
                  if (path.node.id.name === 'processData') {
                    functionCode = generate(path.node.init).code;
                  }
                }
              });
              console.log(functionCode);
              ```
          - **Disadvantages:**
            - Huge set of dependencies for a small piece of work
        - Mark it up with text and do a text replacement so `let mastodon =` disappears
          - **Advantages:**
            - Simple to implement
          - **Disadvantages:**
            - Possibly brittle. Will rely on me not changing the wrapping of the function
              - But, I will notice pretty quickly if I get that wrong
        - Something else? Search and see how others solve this
          - Because I tend to get too carried away at just solving the problem and not look around enough, because honestly, I think just adding some text markers is enough for what I need and I'm inclined to just do that, because it's good enough for my needs.
          - But, let's start by doing a quick search and also ask Claude to help me search, since it's usually good at coming up with unique search patterns
          - Prompt to Claude:
            ```plaintext
            I am working with n8n and want to maintain my workflow as code.
            My workflow uses custom javascript in some of the nodes so I have them stored on my filesystem and I want to extract the function in question and inject and run the function in my node.
            Are there existing solutions for doing this?
            My spontaneous reaction for how to solve it is:
            1. Add markers in text in my file
            2. Extract the content between those markers
            3. Strip the prefix/suffix around the function required for testing the function
            4. Wrap the remaining stuff in what I need to then use it in the workflow and inject it into a workflow template using jq
            ```
          - Claude is questioning my approach as brittle, which is fair, it suggests I package it as a node module instead or some templating that injects the source code of a function. If I can just inject the source code of a function then that'd be awesome, then I'll just make a little node script that outputs the correct thing for me
            - Right, so Claude dreamt up a suggested way of implementing my marker idea.
              And a custom npm module would mean maintaining the code on the server and injecting it into n8n. It totally makes sense if I'm doing more advanced stuff, but for my current situation, I think having a single file trumps that.
    - **Decision:** Mark it up with text and do a text replacement so `let mastodon =` disappears
      - My use-case is so small, this feels like the pragmatic choice until I have more advanced needs
      - I wonder if I should just do all this work in javascript or if I should do what my gut says: a small bash script.
      - Quick overview in my head: upside of using javascript is that I can just load the json into a file really easy, and then output to stdout in a pretty-printed form.
        The logic to process between the markers isn't that hard and I already have the testing setup
      - The other option is to do it in Python since the rest of my blog is in python. But since n8n is more js maybe it makes sense to keep this stuff in the one language
      - And if I keep it with JS then I don't have to deal with jq, I can just do the whole thing in one pass by in JS. I think that'll be easier.

### Designing the extraction
Okay, so what I'll do is create a little helper script that.

1. I can point at a js file and it'll extract out the marker I have specified,.
2. Using the content of the marker, change it slightly so it'll work in place (make it self-calling)
3. Load the n8n workflow file, replace the key in the right place.
4. Pretty-print the json to STDOUT.

I'll make the marker format `//<EXTRACT:name>`, the go convention of programmatic stuff doesn't start with a space and all :p.

### Building the extractor

I wrote up my first tests, ensured the first "do nothing" test passes, and now with my second test in place I'm gonna ask Claude to implement it, because I don't know these node APIs. And claude did that quickly and the implementation seems sane. Claude decided to wrap everything so no errors would bubble up, so I removed that `catch` because any errors should bubble up because I don't want to miss out.

```javascript
describe('extract.fromFile', () => {
    test(`if the markers aren't found, then nothing is returned`, () => {
        var actual = extract.fromFile('testdata/no-markers.txt', 'test')
        assert.strictEqual(actual, '', 'expected an empty string when no match found')
    })
    test(`if the markers are found, the content is returned`, () => {
        var actual = extract.fromFile('testdata/plain-text.txt', 'test')
        assert.strictEqual(actual, 'Hello, World!\n', 'expected the content between the markers')
    })
})
```

I also discovered when done that my tests weren't passing in intellij because it was running the tests from my repo root, so I changed my `Node.js test runner` config to default the working directory to `src/js/` for this repo, because I am deciding now that I'll only ever have javascript stuff there, and I'll only run the tests from that directory. It feels like a decent solution.
Maybe I have to revisit that if I ever introduce a package.json and decide whether it belongs here or in the root, but it probably belongs in `src/js/`, but that's the future 🤷.

Now, Claude did one thing I didn't intend yet (because there isn't any test), which is that it will ignore the whole line the markers are on (which I indicated in the docstring) but I don't have a test for it yet.
I want this behavior so that I don't have to do any special handling to ignore whatever comment marker there is.
So, let's add a test for this even if the code is already implemented. I guess I _could_ remove that comment and reimplement, but that feels like waste, so I won't. Time to be pragmatic instead of dogmatic about the testing.

Hah! Adding the test was good, because I skimmed the code too quickly and it hadn't done what I expected, it was checking the full line. So I actually _do_ have to change the code.

Cool, so I have my extract function.

### Building the workflow updater script

Now I can create a script file and use it. I think I'll keep the script in `src/js/` folder and it'll take the path to the reference workflow file and read it in and parse, and then I'll work it from there.

I won't TDD this file because it should be at the level that I'll notice problems when using it. We'll see how much I'll regret _that_ decision later.

In hope that Claude can do this for me, I started by documenting at the top of my script how I want it to work:

```javascript
/*
 This script's job is to:

Extract the mastodon and bsky functions from n8n.copies.js.

Read the JSON file in the first argument and then replace the nodes for Mastodon and bsky respectively with their functions.

Output the updated JSON object on stdout, pretty-printed
Example: ./update_n8n_workflow.js ../bjorn-now-feed-distribution.json > workflow.json
Will update the node id `e1bd320b-1222-4324-9168-22372d2e667c` so the parameter.status is `={{ ((item) => {... })($('RSS Feed Trigger').item) }}
*/
```

Then I asked Claude to implement it:

```plaintext
implement @src/js/update_n8n_workflow.js as described in it's first comment, use @src/js/extract.js to extract the information. Only implement the mastodon portion right now 
```

My example contained too much information, so claude suggested that it needed to `wrap the extracted function as: ={{ ((item) => {extracted code})($('RSS Feed Trigger').item) }}` but it should be `(...)($('RSS Feed Trigger').item)`, so I told Claude to plan again ` I was unclear: the wrapping is "(extracted code)($('RSS Feed Trigger').item)"`.

```plaintext
Implementation Plan for update_n8n_workflow.js
 1. Import dependencies: Import fromFile from extract.js and Node.js fs module
 2. Read command line arguments: Get the workflow JSON file path from process.argv[2]
 3. Extract mastodon function: Use fromFile('./n8n.copies.js', 'mastodon') to extract the function code
 4. Read workflow JSON: Parse the workflow file
 5. Find and update node: Locate node with id e1bd320b-1222-4324-9168-22372d2e667c and update its parameters.status field to wrap the extracted function as: ={{ ((item) => {extracted code})($('RSS Feed Trigger').item) }}
 6. Output result: Print the updated JSON to stdout with pretty formatting
 The script will be executable with: node update_n8n_workflow.js ../bjorn-now-feed-distribution.json > workflow.json
```

The plan now looks correct, it says "arrow function" instead of "extracted code", which I guess is because it added a step to strip `let mastodon =` from the line, so I'll assume it does the correct thing, either way, this is close enough that manually fixing it will likely be trivial. allons-y!

### Importing the updated workflow

A quick skim of the code and it looks correct, the output also seems correct to me, so let's save it to a file, run jq to verify it's valid json (I assume it is since node didn't bork out), and then upload and see what goes. My saved file locally is what's live now, so if it goes wrong, I can back out easily.

Right, interesting problem: n8n supports importing from a file and then it adds the file content _alongside_ what you already have. So now I have a copy of all my existing nodes and with a 1 at the end. The content of my new Mastodon status node DOES look correct, though. So that's a win
Not quite what I had in mind, so I feel like I'm doing something wrong.
Let's start by asking Claude about this workflow and see if they can push me towards some online docs.
or, n8n has these boxes "I wish this node would…" I can just ask there and see what goes.

Seems like this is working as intended (d'uh) and the way to handle this is doing it by API. And… fair enough, can. so I asked Claude to make me bash script that I could use.
Then it started complaining that I didn't have a name in my file, which I do, so there seems to be a mismatch between the downloaded workflow and what the API expects.
D'oh, I had missed a line in cURL `-d @-` to read the file, so that's on me.

Then I had issues because apparently my downloaded workflow doesn't just work with the API, so Claude and I did some back and forth and finally ended up with this that limits the fields I want to update:

```shell
cat $1 | jq '{
           name,
           nodes,
           connections,
           settings
         }' | \
  curl -X PUT "${N8N_HOST}/api/v1/workflows/${workflow_id}" \
    -H "X-N8N-API-KEY: ${SANITARIUM_N8N_API_KEY}" \
    -H "Content-Type: application/json" \
    -d @-
```

Weirdly, I had to update the `settings` so it only contained the keys `executionOrder` and `errorWorkflow` as the other two values there weren't okay. Whatever, they didn't seem important so 🤷.

### Validating the updated workflow

Now I have uploaded my changed thing, and it's time to verify it works as I want. I'm not entirely sure what I should post to verify it :p.

I was looking at the result from running the update, and unless I always save the result of the update I _might_ rerun from a prevous point when updating. Or, no, because it's a top-level field that I'm ignoring when updating. So it should be fine. But, I think for now, I'll anyway pipe the update stuff _into_ the saved file so it's there and see what changes between runs.

Committed, and tested by posting a scrap about "wow… I really spent 5h doing this? That's longer than I expected." But, I guess the thing I have to keep in mind that this is the difference between "engineering" vs. "just throwing stuff together." If I hadn't invested in the infrastructure stuff for managing this, I would've been done after 30-40m when I updated the code.
The point was the investment in robustness I think I've gained.

## Repeat for Bluesky

Handle the no-link with Bsky too.

### Designing the change

Now, with all that done, time to look into Bsky, there I don't append the links but instead attach a "website card."
There, I guess I'd have to change it so:

1. The body gets the same logic/setup.
2. The logic is repeated in the "Website Card" field, assuming that having an empty value there will do nothing (which I assume it will, Javascript being very used to weird cases of keys not existing, but I should test (and executed with an empty body there, it just worked), so just repeat the same logic in that place)

this is a bit more annoying, will have to do some copy paste, but I can at least handle the consistency by creating a reusable test.

But I'll work on this either tomorrow or later today, it's after 16, and I feel like taking a break. And heading home feels like a good way to clear the head and then continue.

### Implementing reusable tests
**20:03** And it's after dinner, let's see if we can get this in so we can push it through.

What I think I'll do is just do a quick duplication of what I have, don't be clever, just do the dumbest thing possible.
With one caveat: I know the tests are mostly the same, so let's make the tests reusable and configurable and see if that pattern works in node (I bet it does).
Meaning, I want my existing tests for Mastodon to be shared with Bsky but change the limit to 300 char instead of 500.

The way I'll test that is that I'll make a function that returns a closure over my config, then I'll run it by passing in my code to execute and then see if the assertions match. I'm not sure how it'll go with the test runner, but let's see. I.e. something like:

```javascript
function reusableTest(name, maxLength, urlLength) {
  return function(toTest) {
    return () => {
      test(`it does stuff`, () => {
        let actual = toTest(arg)
        assert.strictEqual(actual, "whatever I want")
      })
    }
  }
}
describe('mastodon', reusableTest('mastodon', 500, 23))
```

And another part is, I don't know how Bsky does links. There's something [about facets](https://github.com/bluesky-social/atproto/discussions/3517) and how you can use them to reduce links but a big 🤷 in understanding that. I don't know if I'll care to look this up or not.

I could potentially do some smarts and just attach the URL as a card and remove if it's a single link in the post, which I could make as standard for myself.

Anyway, let's get the tests working now and see what goes first.

Okay, that kinda just worked as expected, a little surprised at how smooth it was. [The commit.](https://github.com/gaqzi/bjorn.now/commit/acd53a5056c11ea11c2d3accac69cf2c7a008cc9)

#### Is this really reusable?
I am getting a bit worried that the setup might be… too fiddly, but I'll feel it out a bit more as I add in bsky. This feels like it's hitting the point where code _looks the same_ but it isn't really reusable, because it looks similar but differs in intent so as we diverge it'll just add more `if`-statements. But, we'll continue going and feel it properly.

the first case: there isn't any clear "a link is always 3 chars" so it'll be counted as whatever the raw text is, so I'll use `-1` to indicate don't do anything (an `if`, urgh).
Spontaneous thought: I could pass in a function to handle the link calculation instead and just assume it sends me the link, so that would sort that problem out nicer and it keeps the test consistent. My favorite the strategy pattern showing up and making my day cleaner, again.

I'll just do that, it's much better than a magic number, and I can create that magic number as a variable from the function call. I know I have to implement this now, so it's the right time to "Tidy First" á Kent Beck. 🙂.

And there we hit the problem it: it's all very similar for good reasons, BUT the logic **has to be different** because the default way where I add the link at the end for Mastodon doesn't apply for bsky, there I can just attach it as a card.
So all the URL counting stuff don't matter.
So, I'm better off copying the tests and changing them slightly, and calling out that they're similar but importantly different, any optimization here is folly.

I only spent ~15m on this, so I don't feel too bad about it. In some other cases it would've worked out, and it does feel good to keep coding instead of just thinking a whole lot before doing anything.

So, `git reset --hard` on those files and a revert on the commit. Now let's start by copying and changing.

And, to get what I need later to decide whether to do the card I'll just look for `msg.endsWith('… more')` and if so, attach the link if it's a `/scrap/` link. So that's pretty straightforward, it does mean I have to include the info, but that's okay.

### Refactoring after working tests
And done,  but looking at how I'm deciding whether something is truncated, I don't get what I'm doing. Why don't I just look at the string and check if it changed? That seems way more straightforward than comparing two fields from the RSS….

So I'm just gonna do that and see what happens, but first, commit my changes, then change the format of how I work.

That was quick, maybe 5m to make the change. I looked at the workflow file and the difference between `contentSnippet` and `encoded:contentSnippet` seems to have to do with newlines and other formatting, so that's not gonna be very useful. Seems like a major brainfart that accidentally ended up working 🤷
(likely that those that didn't need truncating were on a single line)

Okay, next up, now to make sure that `update_n8n_workflow.js` handles bsky as well and updates it.

Went through and updated it, I mostly kept the very procedural code and just added on, maybe I'll clean it up a bit more if I loop back and add Telegram (for Telegram I'm thinking I'll just do the preview in app button intead? but maybe it makes sense to put the scraps in there too, it's no different from the others and there's less links :))

### Testing bsky live

And I made a post that would fit 300 chars about [helping my brother install some RAM](https://bjorn.now/scrap/2025-10-29t213248/), where the point behind is that having done it before gives confidence that instructions just don't give. Whether installing RAM or relying on your tests 😜. And it gave me a chance to see that the logic works.

What does the n8n update endpoint do and how does it work? Becuase it feels like not understanding how it's designed might come and bite me later, so let's not just rely on the vibe coded stuff that _seems_ to be working.

## Wednesday EOD

**21:39** And done, I've finished bsky. Tomorrow I'll be hanging with the niece all day so I'll format and post this devlog when I'm in the office again 🙂
Okay, scrap that (heh), I'll finish Telegram before posting. Then for formatting to post,  I'll do it by creating a script alongside Claude to figure out the formatting. I'll have to brainstorm how then.

## Update Telegram logic

Add the scrap logic to Telegram too (if it's a scrap, only post the text, otherwise the link)

### Configuring Instant Views

Time to get Telegram to be a bit nicer. I overall don't want to force people to click through to my site if they're happy reading where they are. Telegram has these [Instant View](https://instantview.telegram.org/) buttons and I can translate my links to use those instead, so I figure I'll do that in my channel so you can just click and see the full thing without loading my site. I guess this will mess with my statistics a bit (because I use [Plausible](https://plausible.io/) which is doing it all in javascript), but 🤷, for now I'm just happy if people wish to to engage with anything I post.

I did create a preview a couple of months back so I started by taking a link to my site and then copying in what I did last time:

```plain text
~version: "2.1"
site_name: //*[@class="masthead"]/a
article: //article
title: $article//*[@class="title"]
subtitle: $article//*[@class="subtitle"]
author: $article//*[@class="author"]
image_url: //meta[@property="og:image"]
published_date: $article//*[@class="published-at"]
body: $article//*[@class="content"]
```

That looks pretty good, but I'm not seeing the published time in the live preview, the xpath expression looks right to me. And I similarly don't see the image_url, and looking in the template website I don't see that the `<head>` section is part of the example document (From the future: Nope, that's wrong, I was looking at the containing doc and not the iframe, it's all there. Telegram will always do a `GET` for your page to get the current version and then format the page using these rules). So maybe that's why? I'll skim through [the documentation](https://instantview.telegram.org/docs) and see if I can find why.

I see that the `published_date` says "unix time" [in the docs](https://instantview.telegram.org/docs#instant-view-format), so maybe that's the problem? I gave it the element and it's in readable, but I do have the RFC3339 format string in the `<time>` tags `datetime` attribute. Let's keep digging.

Right, so the docs shows that there's a function [@datetime](https://instantview.telegram.org/docs#datetime) that can take an xpath expression and return a unix timestamp, so I likely will have to give it the attribute and then specify the format so it can be converted.

So with that, the pattern should be something like this, which doesn't work, and I think I'm trying to access the property incorrectly in xpath.

```plaintext
@datetime(-2, "en-SV", "yyyy-MM-ddTHH:mm:ssZ"): $article//*[@class="published-at"]['datetime']
published_date: $@
```

I asked Claude how to access it in xpath:

```plaintext
I want to access the property `datetime` on the element matched by this xpath expression (for Telegram Instant View), how?
`*[@class="published-at"]
```

Which gave me the answer that I need to access it by saying `/@datetime`, which __to me__ reads that I "dig into" the element and `@` seems to have to do with attributes/properties of a tag. When I replaced `['datetime']` with `/@datetime` and saved my match then Telegram showed my publish date!

**TIL:** Use `/@<name>` to access the value of an attribute when you've selected an element with XPath.
With the expression `//*[@class="published-at"]` you will get the HTML tag that has `class="published-at"`, and if you then want the `datetime` property you add `/@datetime` to get it.

And now that I have the `published_at` working I'll see if I can figure out how to access my preview image which is available in `<meta property="og:image" content="<url>">`, and I bet the problem is that I'm not going into `/@content` the way I need to. Changed and that worked!

There's this Instant View property called `kicker` which I don't know what it means, so I asked Claude and it said:

> `kicker` is the small text that appears **above** the main headline in article layouts - typically used for:
> 
> - Category labels ("Politics", "Technology")
> - Section names ("Opinion", "Analysis")
> - Eyebrow text ("Breaking News", "Exclusive")

I guess this is some publishing term and it sounds like my "content types" would be fitting here. I.e. post, crumb, link, scrap, etc. which I actually don't show at the moment on my single pages. Maybe I should add that in there? Or should I just skip it? It's part of the menu. Although, I have added it into the `article`'s `class` attribute what category it is, because I have been planning to do custom styling of scraps (pre-emptive code, I know bad, but turns out this bit of unnecessary future planning might be helpful now.)
So, question is, can I strip away the `post` and `single` values from that string only leaving the unique piece?

In the list of [functions](https://instantview.telegram.org/docs#supported-functions) there's a `@match` function that takes a regex, so that _could_ work. Let's see if there's anything else before I go into making a regex (which admittedly can be pretty simple given how it's setup right now)

It seems that's the only function I have. So right now, I'll do it super simple and since my `class` attribute looks like this: `class="post devlog single"` I'll just do `post ([^ ]+)` and then extract the second, the `single` also isn't needed, but since I'm doing this on the `article` element I don't feel the need to do more, I'll just have the rule that the first class is always the post and this will work.
The `@match` function's second argument is which capturing group you want to use. While debugging it was a bit non-obvious to me that the debugger's output included `class="devlog"` but it seems that it shows the full context, but when you add it to the kicker as `$@` (which is the return value of the last function call) then it'll just do the string and not where it was from. 🤷.

```plain text
@match("post ([^ ]+)", 1): $article/@class 
kicker: $@
```

Next up, `author_url` which is a property on the `<a>` tag which contains my name, so let's dig into it: `author_url: $article//*[@class="author"]/@href`.

### Using Instant View links or not?
And with that, I have the Instant View working as I want in the preview. Now to figure out how I use it when posting so others can see it. [The documentation](https://instantview.telegram.org/#publishing-templates) for it says:

> Note that if you send the resulting `t.me/iv?url=...&rhash=...` link to other Telegram users, they will see an Instant View page built using your template (the __rhash__ parameter in the link determines which template is used to create the page).

So all I have to do is wrap my URL to this and it'll work. The downside of that is that then if you click that URL it'll lead to Telegram instead of my site, and it's not obvious to me how to click through to my site. I added the `document_url` but it seems it doesn't show the real URL.
I don't like this. MAYBE what I could do is add a second link that allows the instant preview, as a way of making it simpler for Telegram users. But iunno, it also feels clunky.
I could try to submit my template and see if it gets approved and then it just works.
I asked Claude and it says the same thing, it's not possible, and if you want that then you need to submit it. So that's the only real option, I don't want to completely nerf the readability for Instant View while I also want to make it simpler for others to read it where they are. The same reason I have the full content in the RSS feed. :)
So I added 10 links that should work, looked that they seemed correct, and added them as checked. Then I added the homepage and blog post listing pages and saw that they **don't** have any Instant View, which is what is supposed to happen.

### Final Telegram logic and decision
Which leaves my Telegram posting logic as:

1. If the URL of the item contains `/scrap/` then post the `content` in full (I'll deal with images later, but for now scraps are text-only with no formatting)

2. Otherwise, post only the link so it can be clicked through and if the Instant View is approved then that's available.

And that took about 1.5h to do. Next up, to research how the update endpoint works for n8n, and then to do the formatting of this post and post.

## Understand how n8n updates work

I left a note for myself earlier that I wanted to check how n8n handles the updates, so I can feel more comfortable in not overriding stuff.

### Digging into the source code

I figure it'll be a bit annoying to find this, so I'll just ask Claude to find it for me:

```plaintext
where is the n8n source code for the `PUT` logic for workflow updates?
```

And it did some searches and told me path in the repo is [packages/cli/src/public-api/v1/handlers/workflows/workflows.handler.ts](https://github.com/n8n-io/n8n/blob/n8n%401.116.0/packages/cli/src/public-api/v1/handlers/workflows/workflows.handler.ts#L268) so I went to GitHub and opened.

It does special handling for `settings` and will [only change settings](https://github.com/n8n-io/n8n/blob/f65b6a82a95f0fd298422faa5f6cf3f69bbd3249/packages/cli/src/public-api/v1/handlers/workflows/workflows.service.ts#L107-L112) I have set and otherwise let existing ones be.

Okay, working my way to the [WorkflowRepository](https://github.com/n8n-io/n8n/blob/master/packages/%40n8n/db/src/repositories/workflow.repository.ts#L52) it doesn't implement `update` itself, so it's probably in the base class, so let's see what's there.
The base class comes from `@n8n/typeorm` and I don't know where that is. I looked in the `@n8n` folder on GitHub but didn't see it. I tried pressing `t` and typing it but it doesn't seem to be part of the path. The search showed that there's a `CLAUDE.md` so maybe it contains something useful? (I'll dig a bit first before asking Claude to find it for me).
And there I find this: `**Backend:** Node.js + TypeScript + Express + TypeORM` which seems to indicate that TypeORM might be a general package?
I searched for `TypeORM` and saw a linter step to ensure we only use it in `@n8n/db` folder, so is there a definition of `@n8n/typeorm` in the `db/` folder?
The `package.json` lists the dependency as `"@n8n/typeorm": "catalog:",`, so maybe there's something in this catalog folder (or maybe package?)
I had a gut feel since I saw `pnpm` mentioned and something around monorepos, maybe this is a special `pnpm` thing so I did a search for "pnpm catalog" and found explains it's a "[workspace feature for defining dependency version ranges as reusable constants](https://pnpm.io/catalogs)." So if I get that right, it's how you ensure the same version of TypeORM is used across this entire monorepo. Sounds neat.
So, that means I'll just assume we're doing the bog standard TypeORM stuff so I'll look at that. But I will assume it'll simply do: replace the named keys if they're part of what comes in, because a generic package usually doesn't do more than that.

TypeORM's documentation for update says: `update` - Updates entities by entity id, ids or given conditions. Sets fields from supplied partial entity.
And I read that to mean: we'll replace all keys we see, and the others will not be touched. So I won't accidentally unset any fields I don't change.
SO, maybe then I should try and limit what I send even further since I only really want to update the `nodes` portion, so could I get away with only sending that? And the answer is no, because then it gives an error that I need to provide `connections`.

### Adding "only update if version is what I expect on the remote"

But, it's fine, I'm anyway saving the version in the repo after each update, so I would only loose things if the version live is different from what I have. Which for now, I don't worry about. I COULD do a check to see that the current version is the same as what I have downloaded or warn. I guess that _would_ be pretty tiny effort, and therefore worth it since all you'd have to do to sort it out is run `get-workflow` and then recreate the update and check it.
So… letting me know there's a mismatch WOULD be useful.

The way to do that then is: `jq -r '.versionId' bjorn.now-feed-distribution.json` gives me the version id, so then I would have to pull down the current version of the workflow and check the version number is the same:
`./get-workflow | jq -r '.versionId'`
and then compare it, so… screw it, let's put that in the update script.

```shell
# Only update the workflow if the `.versionId` ISN'T the same as the server,
# because we're downloading the workflow and then applying our updates to it.
# This intends to avoid overwriting anything we didn't expect.
localVersion=$(jq -r '.versionId' "$1")
serverVersion=$(workflow_id=$workflow_id ./get-workflow 2>/dev/null | jq -r '.versionId')
if [ "$localVersion" != "$serverVersion" ]; then
  echo "The local workflow file ($1) is stale to the server version" >&2
  echo "  local version : ${localVersion}" >&2
  echo "  server version: ${serverVersion}" >&2
  echo >&2
  echo "Hint: Pull down the latest version as and recreate:" >&2
  echo "  ./get-workflow > bjorn.now-feed-distribution.json" >&2
  echo "  ./create-update" >&2
  exit 2
fi
```

Added a hint to myself in case I forget.

## Final thoughts

This entire endeavour got a bit more robust than what I've had before with my n8n setup, but that's because I'm planning to add more functionality to my POSSE setup. So I wanted to make sure I don't create more of a mess for myself as I change things, and create more things to check.

This isn't 100% the production level I would do but it's good enough for where I am. The "create the update" script is pretty rough, but I also expect that I will *very rarely* change it, and it's built around a couple of assumptions that I don't see changing. So keeping it hacky, or more as disposable, feels okay to me. If I had more people working on this I might not be, but for now, there's enough guard rails.

I'm happy I decided to add the optimistic check that we're updating against the version on the server, it's the kind of thing that was _really_ straightforward and simple to add and it'll rarely fail, but it'll warn in case I end up doing click-ops and forget to sync back to the repo.
