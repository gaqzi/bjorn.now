---
authors: ['björn']
date: '2025-07-07T21:50:00+08:00'
lastmod: '2026-03-20T09:23:00+01:00'
location: Singapore
title: Working with Go's test cache on CI
subtitle: 'be fast by avoiding work, while doing the important work'
tags:
  - how-to
  - golang
  - ci
  - testing
  - integration-testing
aliases:
  - "/blog/2025/07/07/caching-go-on-ci-without-surprises/"
  - "/blog/2025/07/07/working-with-gos-test-caching-on-ci/"
---

I was trying to speed up our slow CI by caching Go builds. The easy win was caching Go's module downloads (via `GOPATH`), but when I added `GOCACHE` for the build cache, I got a pleasant surprise: the tests were caching too. 🥳

I shared the change for review, and a colleague raised a great point: "What about our black box integration tests?" These tests hit APIs and external services that Go can't track as dependencies. If they cache when they shouldn't, we might miss real failures: the tests would pass because they didn't re-run, not because the code actually works.

<details>
<summary><strong>TL;DR:</strong> I found three ways to handle Go test caching on CI, they are:</summary>

| Approach | Changes Needed | Test Caching |
|----------|---------------|--------------|
| `go clean -testcache` | CI config only | ❌ None |
| `-count=1` | Every test invocation | ❌ None |
| Environment variables | Shared code/library once | ✅ Full |

**`go clean -testcache`** — wipe all test cache before running. No code changes, no test caching.

**`-count=1`** — skip cache for a specific `go test` invocation. Need to add it everywhere.

**Environment variables** — read your CI's commit SHA (e.g. `GITHUB_SHA`, `DRONE_COMMIT_SHA`) in your test setup. Go auto-invalidates the package's test cache when the value changes. Unit tests still cache, integration tests re-run on new commits as long as you read the variable once in the package. A helper to ensure it doesn't cache:

```go
func IsIntegrationTest(t *testing.T) {
    t.Helper()
    _ = os.Getenv("GITHUB_SHA")
}
```

Key behavior:
- Invalidation is **per-package**, not per-test
- Reading env vars through library calls still triggers invalidation
- `go test` with no package target never caches
- Debug caching decisions with `GODEBUG=gocachetest=1`
</details>

## The Fundamental Problem

When my colleague warned me about integration test caching, I realized we had a bigger problem than just my PR. How could I fix this across our entire org? We've got ~250 repos, and asking every team to remember special flags or change their test execution wasn't going to fly. I needed something that would just work everywhere with minimal changes.

The fundamental issue: our black box integration tests don't "declare their dependencies" to the Go compiler, so it doesn't know that something the test is critically dependent upon has changed and requires a rerun (and practically, neither do we really), because they test network services and external binaries that Go has no visibility into. I always have to run these tests.

I wanted the caching benefits without the risk, ideally with minimal changes since we have lots of codebases that could benefit from this caching improvement. Since our black box integration tests use a shared internal library, I was hoping to find a solution I could implement once there rather than asking teams to modify individual tests or change how they execute them.

## So... How Do I Make This Work?

I started by looking for the obvious solutions, there's probably a flag to ignore the test cache, right? And there were two straightforward options: `go clean -testcache` and `-count=1`. But here's the thing, both of them throw away ALL test caching, which felt like using a sledgehammer when I needed a scalpel.

Then I remembered reading something about environment variables, and files, affecting test caching. I went into `go help test` and I remembered right, tests that read environment variables get invalidated when those variables change, so since this is about CI, and I know that CI systems give us unique commit SHAs as env vars… and we have a shared library to help write black box integration tests… so I can make the fix once in that library and everyone gets this benefit!

Alright, that gives me three options, how do they compare?

**Simple Option: `go clean -testcache`**
- Pro: Dead simple - add one line to your CI config, no test changes needed
- Con: Zero caching benefit for tests
- When to use: Safest solution that still gives you build benefits without changing scripts or tests

This works by creating [a file with the current Unix time in nanoseconds](https://github.com/golang/go/blob/665af869920432879629c1d64cf59f129942dcd6/src/cmd/go/internal/test/test.go#L844-L848) and then, whenever Go runs tests, it checks if the cached test is newer than that timestamp. I appreciate the simplicity: the cache cleaner doesn't need to understand which cached items are tests (and there are only hashes in that folder), it just sets a "tests are invalid after this moment" marker and the code skips it or not.

**Explicit Option: `-count=1`**
- Pro: Granular control per `go test` invocation
- Con: Need to change test execution and remember it everywhere, easy to miss (especially in monorepos with many go.mods)
- When to use: Only some tests need cache invalidation

This is the one you'll see when people ask how to make Go not cache tests, for our situation not super useful, but mentioning it for completeness.

**Elegant Option: Environment Variables**
- Pro: Automatic cache invalidation on CI when needed, maximum caching benefit when possible
- Con: Requires thoughtful test design
- When to use: You have enough tests that the speedup matters and you're willing to be intentional about cache invalidation

Or laid out visually: 

| Approach | Changes Needed           | Test Caching | Safety |
|----------|--------------------------|--------------|--------|
| `go clean -testcache` | CI config only           | ❌ None | ✅ Safest |
| `-count=1` | Every test invocation    | ❌ None | ✅ Safe |
| Environment variables | Shared code/library once | ✅ Full | ✅ Safe* |

*_When implemented correctly_

### How the Environment Variable Approach Works

This works because Go invalidates the entire package's test cache whenever an environment variable it depends on changes, and most CI systems expose a unique commit SHA as an environment variable. For example,

- GitHub Actions: `GITHUB_SHA`
- Drone CI: `DRONE_COMMIT_SHA`

When your integration test reads this variable, Go automatically invalidates the cache for that package whenever you push new code. The key insight: you don't need to *use* the variable meaningfully, just *read* it. One thing to keep in mind: consider keeping integration tests in separate packages from unit tests to avoid invalidating unit test caches unnecessarily when only the integration tests need cache invalidation.

```go
package integrationtesting

func IsIntegrationTest(t *testing.T) {
	t.Helper()
	// This ensures that we invalidate the cache
	// on CI whenever we have a new git SHA
	_ = os.Getenv("DRONE_COMMIT_SHA")
}

// ... another file relying on integrationtesting

func TestAPIIntegration(t *testing.T) {
	integrationtesting.IsIntegrationTest(t)

	// Your actual integration test
	resp := callAPIEndpoint()
	assert.Equal(t, expected, resp)
}
```

## Understanding How It Actually Works

I was getting worried about edge cases. The Go docs said tests won't cache if environment variables change, but what exactly did that mean? Would reading an env var in one test invalidate *all* tests everywhere? Just that package? What if the variable is read through a library call?

I did some searching and found the [testlog package][testlog], which is how Go implements the tracking of when env vars are read and files opened. That gave me a good sense of how it should behave, so I made an experiment to validate what I expected from the documentation and the code I found.

### The Experiment Results

I created [three test packages][experiment] to understand the boundaries:
- One that reads `DRONE_COMMIT_SHA` directly
- One that reads it through a library call
- One that doesn't read any environment variables

Then I ran [nine scenarios to test my assumptions](https://github.com/gaqzi/experiment-go-test-caching/blob/main/test.sh): What happens when I set the variable? Does package listing matter (`./...` vs manual package lists)? What about `go test` with no arguments?

Key findings:
- **Package-level invalidation**: All tests in a package get invalidated if *any* test reads the variable and the variable changes,
- **Library calls count**: Reading env vars through dependencies still invalidates the cache
- **Package listing doesn't matter**: `./...`, manual lists, even `./` all cache the same way
- **No arguments = no cache**: `go test` without targeting never caches
- **File-level targeting = no cache**: `go test file_test.go` also never caches

The big takeaway: Go runs tests per package, and packages are run in parallel. If any test in the package touches an environment variable, the entire package's cache depends on that variable's value, so the cache is invalidated when the value is different on the next run.

Or as a semi-flowchart:
```text
Package reads env var? 
    Yes → Env var value changed? 
              Yes → Cache invalid
              No  → Cache valid
    No → Cache valid
```

This made me comfortable that the approach was predictable and wouldn't have surprising edge cases, especially because the way [testlog] works is by simply recording that _something_ called `os.Getenv` with this value, and it doesn't know which test or from where, just that in the course of running these tests this happened. Nice and simple.

If you want to explore how Go makes decisions around caching yourself, you can run tests with `GODEBUG=gocachetest=1` to see Go's caching decisions in real time. There are more debugging variables available in `go help cache`.

## The Results

We cut our CI times in half with this caching approach, and I'm confident it's safe to roll out widely because I understand exactly how it works and I can make the required changes to our shared integration testing library so it will just work for the standard case.

What I appreciate about Go's design here is how it avoids clever optimizations in favor of predictable behavior. I knew caching wasn't just on/off, but I wasn't sure if there would be complex edge cases to worry about. Instead, Go picks the straightforward solution: package-level invalidation that's easy to reason about.

The "bigger packages than you think, but still not huge" philosophy means we get plenty of caching benefit, while keeping the invalidation scope manageable, and if we need finer control, we can always split into more packages.

And that's the thing, Go just picks the simple and boring solution that works, it's why I love working with Go. 😁

---

*The [full experiment is available][experiment] if you want to dig into it yourself.*  
*[Presentation slides](https://speakerdeck.com/gaqzi/working-with-gos-test-cache-on-ci) from the Singapore Go meetup*

[testlog]: https://github.com/golang/go/blob/6c3b5a2798c83d583cb37dba9f39c47300d19f1f/src/internal/testlog/log.go#L49-L54
[experiment]: https://github.com/gaqzi/experiment-go-test-caching
