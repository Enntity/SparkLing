# SparkLing cards

The README banner and social preview use the SparkQwen arcade frame and SparkInkling’s Press Start 2P layout. The three score rows come from the [BF16-head qualification](../../results/2026-11-23/bf16-head-qualification.json). Eight-client prose is aggregate throughput.

To render both cards, install Pillow, obtain the Press Start 2P font (SIL Open Font License 1.1) and use the two base PNGs from [SparkQwen at bd26c6d](https://github.com/Enntity/sparkqwen/tree/bd26c6d/docs/assets). From the SparkLing repo root, run:

```sh
python3 docs/assets/make_cards.py ../sparkqwen/docs/assets /path/to/PressStart2P-Regular.ttf docs/assets
```

The banner is 2172 × 724. The social preview is 1733 × 907 and also has a JPEG export for GitHub. [SparkInkling renderer](https://github.com/Enntity/sparkinkling/blob/27e42a6/docs/assets/make_cards.py)
