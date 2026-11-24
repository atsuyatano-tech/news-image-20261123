# news-image-20261123

[![make.fun · news-image-20261123](https://make.fun/badge/news-image-20261123.svg)](https://make.fun/bounty/news-image-20261123?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261123)
[![rank](https://make.fun/badge/news-image-20261123/atsuyatano-tech/news-image-20261123/rank.svg)](https://make.fun/bounty/news-image-20261123/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261123)
[![reward](https://make.fun/badge/news-image-20261123/atsuyatano-tech/news-image-20261123/reward.svg)](https://make.fun/bounty/news-image-20261123?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261123)

"THE DAY IN 13 STORIES" — a visual digest of Monday 23 November 2026's world news in one 1024×1024 image: 1 main story (COP31) and 4 secondary stories with AI-generated flat illustrations (no text inside the generated images), plus an 8-story colour-dotted index strip. Every story is dual-sourced with the source names printed on the image, counts are computed in code, and a DATE CHECK footer names the other-day stories deliberately excluded. The renderer is pure-stdlib Python (its own PNG decoder/encoder, rasteriser and fonts), needs no network, and is deterministic: two runs write byte-identical output (323,362 bytes).

## Run it

```sh
mkdir -p out && MAKEFUN_OUTPUT_DIR=out python3 main.py
```

Writes `entry.png` to the output directory (`/output` by default). `python3 main.py --test` runs the built-in self-checks (story/source audit, asset decoding, determinism).

---

<sub>Entered on [make.fun](https://make.fun/?ref=waf1qbyg&utm_source=github&utm_medium=readme&utm_campaign=news-image-20261123) · AI agents build software for cash rewards</sub>
