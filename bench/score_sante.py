# SPDX-License-Identifier: AGPL-3.0-only
"""Compare Air-VL top-five receipts on the same BF16 prompts and vocabulary bins."""
import argparse
import json
import math
from pathlib import Path
from statistics import mean


def load(paths):
    samples = {}
    for path in paths:
        with path.open() as stream:
            for line in stream:
                record = json.loads(line)
                if record.get('choice'):
                    samples[record['request_sha256']] = record['choice']
    return samples


def score(series):
    names = list(series)
    keys = set.intersection(*(set(requests) for requests in series.values()))
    metrics = {name: dict(continuations_equal=0, teacher_top1_equal=0) for name in names[1:]}
    variation = {name: [] for name in names[1:]}
    shared_sizes = []
    continuations = 0
    for key in sorted(keys):
        choices = {name: requests[key] for name, requests in series.items()}
        rows = {name: choice['logprobs']['top_logprobs'] for name, choice in choices.items()}
        if len({len(row) for row in rows.values()}) != 1:
            raise ValueError(f'tokenization differs for {key}')
        gold = names[0]
        if len(rows[gold]) == 1:
            continuations += 1
            for name, metric in metrics.items():
                metric['continuations_equal'] += choices[name]['text'] == choices[gold]['text']
            continue
        # Echo includes the first token (no prediction) and one generated token.
        for position in range(len(rows[gold]) - 1):
            if not all(row[position] for row in rows.values()):
                continue
            probabilities = {name: {t: math.exp(lp) for t, lp in row[position].items()}
                             for name, row in rows.items()}
            shared = set.intersection(*(set(p) for p in probabilities.values()))
            shared_sizes.append(len(shared))
            reference = probabilities[gold]
            for name, metric in metrics.items():
                p = probabilities[name]
                metric['teacher_top1_equal'] += max(p, key=p.get) == max(reference, key=reference.get)
                differences = [p[t] - reference[t] for t in shared]
                # Collapse all remaining tokens into one final bin.
                variation[name].append((sum(map(abs, differences)) + abs(sum(differences))) / 2)
    if not shared_sizes:
        raise ValueError('no matched teacher-forced positions')
    for name, metric in metrics.items():
        metric['mean_coarsened_total_variation'] = mean(variation[name])
    return dict(free_continuations=continuations, teacher_positions=len(shared_sizes),
                mean_shared_top5_tokens_per_position=mean(shared_sizes), compared=metrics)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('results', type=Path)
    parser.add_argument('variants', nargs='+', help='file prefixes such as mx nv nv-fast mlp4')
    args = parser.parse_args()
    runs = {'bf16': load([args.results/'bf16-quality.jsonl', args.results/'bf16-teacher.jsonl'])}
    for name in args.variants:
        runs[name] = load([args.results/f'{name}-quality.jsonl'])
    print(json.dumps(score(runs), indent=2))


if __name__ == '__main__':
    main()
