---
authors: ['björn']
date: '2026-01-10T14:07:39+01:00'
lastmod: '2026-01-10T14:07:39+01:00'
location: Sweden
title: 'Write out colon subcommands explicitly because wildcard colons trigger prefix matching'
tags:
  - claude-code
daily: ['2026-01-10']
series: ['working-with-genies']
---
Write out colon subcommands explicitly for [Claude Code permissions](https://code.claude.com/docs/en/iam#tool-specific-permission-rules) because `test:*` doesn't match `test:unit` (prefix matching treats them as separate commands), and the fallback `test*` is too broad (matches `testAndDestroyEnvironment`).

For example:

```javascript
{
  "permissions": {
    "allow": [
      "Bash(pnpm test:unit:*)", // Allows pnpm test:unit --arg etc.
      "Bash(pnpm test:e2e:*)",
      "Bash(pnpm test*)"        // ❌ <- will allow testAndDestroyEnvironment
    ]
  }
}
```

**Note:** Tested with Claude Code v2.1.3
<!--more-->
