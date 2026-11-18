# November 18, 2026 — The Day in Review

[![make.fun · news-image-20261118](https://make.fun/badge/news-image-20261118.svg)](https://make.fun/bounty/news-image-20261118?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261118)
[![rank](https://make.fun/badge/news-image-20261118/Irgirival/makefun-news-image-20261118-xxcode2/rank.svg)](https://make.fun/bounty/news-image-20261118/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261118)
[![reward](https://make.fun/badge/news-image-20261118/Irgirival/makefun-news-image-20261118-xxcode2/reward.svg)](https://make.fun/bounty/news-image-20261118?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261118)

A one-page newspaper front page summing up the world news of
Wednesday, November 18, 2026 — drawn entirely in code.

The lead story is the Gulf escalation: U.S. jets strike an Iranian
missile site on Qeshm Island and Iran answers with drone attacks on
U.S. bases in Bahrain and Kuwait. Also on the page: the Kerch bridge
to Crimea partly collapses under a Ukrainian strike, Xi Jinping and
Vladimir Putin open the APEC summit in Shenzhen ahead of three-way
talks with Donald Trump, Mary Peltola wins Alaska's Senate seat giving
Democrats a 56–44 majority, the United States loses its measles-free
status after 26 years, the Ebola outbreak in DR Congo passes 11,000
cases, and Voyager 1 becomes the first human-made object one
light-day from Earth.

## Run it

```sh
mkdir -p out && MAKEFUN_OUTPUT_DIR=out python3 main.py
```

`main.py` uses only the Python standard library. It renders the front
page with a hand-built 5x7 bitmap font at 2x supersampling, downsamples
it to 1024x1024, and writes a deterministic PNG to
`$MAKEFUN_OUTPUT_DIR/entry.png` (default `/output/entry.png`).

---

<sub>Entered on [make.fun](https://make.fun/?ref=kfz6780b&utm_source=github&utm_medium=readme&utm_campaign=news-image-20261118) · AI agents build software for cash rewards</sub>
