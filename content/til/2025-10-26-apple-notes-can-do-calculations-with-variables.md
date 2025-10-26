---
authors: ['björn']
date: '2025-10-26T12:35:12+01:00'
lastmod: '2025-10-26T12:35:12+01:00'
location: Sweden
title: 'Apple Notes can do calculations with variables'
tags:
  - macos
  - productivity
daily: ['2025-10-26']
series: []
image: /img/2025/10-tv-bench-calculations.jpeg
---
Apple Notes can evaluate calculations with variables that update as you change them.
The variable name has to be "one word,"
so usual `camelCase` or `PascalCase` will likely do you best.

I realized this while trying to calculate what height TV bench I should get:

{{< figure src="/img/2025/10-tv-bench-calculations.jpeg" caption="The center of the TV should be about eye level, so what height bench should I get given myself and the sofa? Seems around 60cm will be good." alt="Apple Notes calculations determining TV bench height using variables for TV size, sofa height, and eye level" >}}

Annoyingly, you can't declare a variable and see its result in one step. 
I found two options for this, and you decide which you prefer.

If you're okay with an extra line you can show it by declaring the variable again, just let notes fill in the part after the `=`:
```text {class=no-copy-button}
MyValue=25*4
MyValue=100
```

Or, instead, write the calculation first, 
and let Notes show the result, then add the variable name.

First, do the calculation:
```text {class=no-copy-button}
25*4=<wait for Notes to autofill>
```

Second, name the variable by adding the name and `=` at the front of the line:
```text {class=no-copy-button}
MyValue=25*4=100
```

I naturally ended up doing this second while I was working it through, 
since I wanted to see the result first, and then I named the variable.

Notes also handle some [unit conversions](https://support.apple.com/en-sg/guide/iphone/iph69d274dde/26/ios/26) for you:
```text {class=no-copy-button}
The average daily temperature in Singapore as Fahrenheit is: 
0f + 32c = 89.6f

How many Swedish Krona do I get from one SGD right now?
0sek + 1sgd = 7.22 SEK
```

I started on my phone taking Notes,
and was surprised to realize I didn't have to fire up Python on my computer to finish it. 
A new useful tool that I always carry with me. 🙂

---

Documentation links to Apple:
- [for iOS](https://support.apple.com/en-sg/guide/iphone/iphb9c2b948f/ios)
- [for macOS](https://support.apple.com/en-sg/guide/notes/apda85974595/mac)
