---
authors: ['björn']
date: '2026-01-10T14:30:41+01:00'
lastmod: '2026-01-10T14:30:41+01:00'
location: Sweden
full: false  # set to true if the full thing should be shown in listings
title: 'Claude Code sandbox exclusion requires both permissions.allow and sandbox.excludedCommands'
tags: ['claude-code']
daily: ['2026-01-10']
series: ['working-with-genies']
---
Add commands to both `permissions.allow` and `sandbox.excludedCommands` to run them outside [Claude Code's sandbox](https://code.claude.com/docs/en/settings#sandbox-settings) by default, because `allow` grants permission to run at all and `excludedCommands` runs them unsandboxed.

```javascript
{
  "permissions": {
    "allow": [
      "Bash(pnpm test:unit:*)",
      "Bash(pnpm test:e2e:*)"
    ]
  },
  "sandbox": {
    "excludedCommands": [
      "pnpm test:unit:*",    // Same commands, different purpose
      "pnpm test:e2e:*"
    ]
  }
}
```

**Note:** Tested with Claude Code v2.1.3
<!--more-->
