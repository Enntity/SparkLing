# SPDX-License-Identifier: AGPL-3.0-only
"""Teacher-forced next-token distributions for fixed passages: one /v1/completions
request per passage with echo, logprobs=5 and max_tokens=1, so every prompt
position returns the token's log-probability and the top five candidates.
usage: dist_ling.py PORT MODEL OUT.jsonl"""
import json, sys, urllib.request

PASSAGES = {
    "prose": ("The ferry left the harbour an hour late, and by the time it cleared the breakwater the light had "
              "already gone soft and yellow over the water. Mara stood at the rail with her hands in her coat "
              "pockets, watching the town shrink into a line of white houses and the slow arc of the lighthouse. "
              "She had promised herself she would not look back, and she was looking back anyway, counting the "
              "windows she could still recognise: the bakery, the post office with its green door, the room above "
              "the chandler's shop where she had lived for six winters and learned to sleep through the foghorn."),
    "explain": ("A heat pump moves heat rather than making it. In winter it pulls warmth from the outside air, even "
                "when that air feels cold, by evaporating a refrigerant at a very low temperature. A compressor then "
                "squeezes the vapour, which raises its temperature well above that of the room, and the hot gas "
                "gives up its heat indoors as it condenses back into a liquid. An expansion valve drops the pressure "
                "again and the cycle repeats. Because the electricity only drives the compressor and fans, a heat "
                "pump can deliver three or four units of heat for every unit of electrical energy it uses."),
    "python": ("def merge_intervals(intervals):\n    \"\"\"Merge overlapping closed intervals and return them sorted.\"\"\"\n"
               "    if not intervals:\n        return []\n    ordered = sorted(intervals, key=lambda pair: pair[0])\n"
               "    merged = [list(ordered[0])]\n    for start, end in ordered[1:]:\n        last = merged[-1]\n"
               "        if start <= last[1]:\n            last[1] = max(last[1], end)\n        else:\n"
               "            merged.append([start, end])\n    return [tuple(pair) for pair in merged]\n\n\n"
               "def test_merge_intervals():\n    assert merge_intervals([(1, 3), (2, 6), (8, 10)]) == [(1, 6), (8, 10)]\n"
               "    assert merge_intervals([(5, 7), (1, 2)]) == [(1, 2), (5, 7)]\n    assert merge_intervals([]) == []\n"),
    "json": ('{"orders": [{"id": "A-1042", "customer": "Harbor Street Bakery", "items": [{"sku": "FLR-25", '
             '"name": "Bread flour 25 kg", "quantity": 4, "unit_price": 31.5}, {"sku": "YST-500", "name": '
             '"Dry yeast 500 g", "quantity": 2, "unit_price": 8.25}], "currency": "EUR", "status": "shipped"}, '
             '{"id": "A-1043", "customer": "Northgate Cafe", "items": [{"sku": "SGR-10", "name": "Cane sugar 10 kg", '
             '"quantity": 3, "unit_price": 14.0}], "currency": "EUR", "status": "pending"}], "page": 1, '
             '"page_size": 2, "total": 57}'),
    "math": ("A train leaves the station at 9:15 and travels at 80 km per hour. A second train leaves the same "
             "station at 10:00 on a parallel track at 110 km per hour. By 10:00 the first train has travelled "
             "80 times 0.75, which is 60 km. The second train gains 110 minus 80, which is 30 km every hour. To close "
             "a gap of 60 km at 30 km per hour takes 60 divided by 30, which is 2 hours. So the second train "
             "catches the first at 12:00, when both are 110 times 2, which is 220 km from the station."),
    "dialogue": ("User: My sourdough starter smells like nail polish remover. Did I ruin it?\nAssistant: Not at all. "
                 "That sharp, solvent-like smell usually means the yeast and bacteria are hungry and producing "
                 "acetone-like by-products. Discard all but a few spoonfuls, feed it equal weights of flour and water, "
                 "and keep it somewhere a little warmer. After two or three regular feedings the smell should turn "
                 "mild and yoghurt-like again.\nUser: How do I know when it is ready to bake with?\nAssistant: Look "
                 "for it to roughly double within four to eight hours of a feeding, with a domed top and plenty of bubbles."),
    "chinese": ("秋天的早晨，山间的雾气还没有散去。老张背着竹篓沿着石阶往上走，路边的枫叶已经红了一大半。"
                "他每年这个时候都要上山采蘑菇，这条路他走了三十多年，哪里有一块松动的石头，哪里转弯处长着一棵老松树，"
                "他都记得清清楚楚。走到半山腰的凉亭时，太阳终于从云层后面露了出来，整个山谷一下子明亮起来。"
                "他放下竹篓，喝了一口水，看着远处的村庄升起了袅袅炊烟。"),
    "list": ("Packing list for a three-day hike in late autumn:\n1. Waterproof jacket and trousers\n2. Two merino base "
             "layers\n3. Insulated mid layer\n4. Warm hat and light gloves\n5. Three pairs of wool socks\n6. Headlamp with "
             "spare batteries\n7. Map, compass and a charged phone\n8. Water filter and two one-litre bottles\n9. Stove, "
             "fuel and a small pot\n10. First-aid kit with blister plasters\n11. Food for three days plus one spare meal\n"
             "12. Lightweight tent, sleeping bag rated to minus five, and a sleeping mat"),
}

def main():
    port, model, out = sys.argv[1], sys.argv[2], sys.argv[3]
    with open(out, "w") as f:
        for name, text in PASSAGES.items():
            body = dict(model=model, prompt=text, max_tokens=1, temperature=0, seed=31, echo=True, logprobs=5)
            req = urllib.request.Request(f"http://127.0.0.1:{port}/v1/completions", json.dumps(body).encode(),
                                         {"Content-Type": "application/json"})
            lp = json.load(urllib.request.urlopen(req, timeout=600))["choices"][0]["logprobs"]
            f.write(json.dumps(dict(passage=name, tokens=lp["tokens"], token_logprobs=lp["token_logprobs"],
                                    top_logprobs=lp["top_logprobs"])) + "\n")
    print(out)


if __name__ == "__main__":
    main()
