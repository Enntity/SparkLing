# LingSante demo

A one-page demo of LingSante-3.1-air-VL served by SparkLing on one DGX Spark. Each of its three scenes makes live calls to the model, and the page shows how long each call took. [Recorded run](run-results.json)

| Scene | What the model does | Recorded on November 26, 2026, SparkLing 0.1.3 |
| --- | --- | --- |
| Chart review | Reads a six-year chart for one synthetic patient (581 documents, 51,349 tokens) and lists missed follow-ups, renal dosing problems, dangerous combinations and lab trends | First token after 25.4 s (2,025 tokens/s), then 52.2 tokens/s. A follow-up question about the cached chart got its first token in 1.9 s. |
| Film and labs | Reads a chest radiograph, then reads the radiograph and a lab report together and files a structured note through a forced tool call | Radiograph read in 3.5 s; note in 11.7 s |
| Triage | Triages eight emergency patients, all sent at once | All eight answered in 6.8 s |

The chart hides four problems: a lung nodule never followed up, NSAID + ACE inhibitor + spironolactone, kidney function falling with potassium rising, and metformin at eGFR 27. The model found all four in the recorded run. In earlier runs it missed a penicillin allergy against a later amoxicillin-clavulanate prescription, so that problem is not in this chart. Thinking is off in every scene. With thinking on, the chart review spent its whole 4,000-token budget reasoning, which took 127 s.

This is a research demonstration, not medical advice. Every patient, chart and lab value is synthetic.

## Run it

Start LingSante with `./start.sh --model lingsante-3.1-air-vl up`, then, from this directory:

```sh
python3 server.py            # serves the page on 127.0.0.1:8700, proxies /v1 to 127.0.0.1:8897
```

Open `http://127.0.0.1:8700/?autoplay=1`, or open the page without `autoplay` and press the space bar. Under LLooM, point `server.py` at the engine port (`python3 server.py 8700 PORT`). `server.py` also sends the eight triage requests to the engine together, because a browser opens at most six connections to one host. `record.py` captures the page at 1920 × 1080 with Playwright. Playwright starts recording on a blank white page, so cut the first 1.5 s (`ffmpeg -i in.webm -ss 1.5 …`) to open on the title card.

`python3 make_chart.py data/chart.txt` and `python3 make_labs.py data/labs-1182.png` rebuild the synthetic chart and lab report. The chart comes out identical on every run; the lab report needs Pillow.

## Image credit

`data/cxr-lll-pneumonia-effusion-1024.jpg`: "Left lower lobe pneumonia associated with a small left sided pleural effusion" by James Heilman, MD, [CC BY 3.0](https://creativecommons.org/licenses/by/3.0/), via Wikimedia Commons, downscaled to 1,024 pixels wide.
