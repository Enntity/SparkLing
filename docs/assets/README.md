# SparkLing cards

The README banner and social preview use the SparkQwen arcade frame and SparkInkling’s Press Start 2P layout. The three rows are SparkModelBench medians on one DGX Spark, with Ling's thinking on: code decode, structured decode and the aggregate of eight concurrent short-code requests from the optional concurrency lane. Ling-3.2-air is measured on 0.1.5 (Atlas `f9d0ebf95`); LingSante-3.1-air-VL carries forward 0.1.4's published run. `make_cards.py` reads them from the published result files. [Scorecard](../../results/sparkmodelbench-v0.1.5/CARD.md)

To render both cards, install Pillow, obtain the Press Start 2P font (SIL Open Font License 1.1) and use the two base PNGs from [SparkQwen at bd26c6d](https://github.com/Enntity/sparkqwen/tree/bd26c6d/docs/assets). From the SparkLing repo root, run:

```sh
python3 docs/assets/make_cards.py ../sparkqwen/docs/assets /path/to/PressStart2P-Regular.ttf docs/assets
```

The banner is 2172 × 724. The social preview is 1733 × 907 and also has a JPEG export for GitHub. [SparkInkling renderer](https://github.com/Enntity/sparkinkling/blob/27e42a6/docs/assets/make_cards.py)
