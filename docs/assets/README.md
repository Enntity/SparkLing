# SparkLing cards

The README banner and social preview use the SparkQwen arcade frame and SparkInkling’s Press Start 2P layout. The three rows show counting, prose and Python decode speeds of the published 0.1.0 image in its default setup: Ling-3.2-air with native drafting and LingSante-3.1-air-VL with Ling's borrowed drafter, one stream each on one DGX Spark. [Release receipts](../../results/2026-11-25/release)

To render both cards, install Pillow, obtain the Press Start 2P font (SIL Open Font License 1.1) and use the two base PNGs from [SparkQwen at bd26c6d](https://github.com/Enntity/sparkqwen/tree/bd26c6d/docs/assets). From the SparkLing repo root, run:

```sh
python3 docs/assets/make_cards.py ../sparkqwen/docs/assets /path/to/PressStart2P-Regular.ttf docs/assets
```

The banner is 2172 × 724. The social preview is 1733 × 907 and also has a JPEG export for GitHub. [SparkInkling renderer](https://github.com/Enntity/sparkinkling/blob/27e42a6/docs/assets/make_cards.py)
