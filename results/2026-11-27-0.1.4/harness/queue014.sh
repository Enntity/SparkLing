#!/usr/bin/env bash
# SparkLing 0.1.4 release queue: release checks (drafted and plain), then SparkModelBench full + concurrency, Ling then LingSante.
set -u
cd ~/models/sparkling/claude-runs
IMG=ghcr.io/enntity/atlas-sparkling:c523fbc3852c
echo "start $(date -u +%H:%M:%SZ)"
FULL=1 ./rel014.sh ling-spark $IMG ling-3.2-air spark
DRAFTER=none ./rel014.sh ling-spark-plain $IMG ling-3.2-air spark
FULL=1 ./rel014.sh sante-spark $IMG sante-air-vl spark
DRAFTER=none ./rel014.sh sante-spark-plain $IMG sante-air-vl spark
echo "checks done $(date -u +%H:%M:%SZ)"
./smb014.sh up ling && { ./smb014.sh bench ling low; ./smb014.sh bench ling low concurrency; ./smb014.sh down ling; }
./smb014.sh up sante && { ./smb014.sh bench sante low; ./smb014.sh bench sante low concurrency; ./smb014.sh down sante; }
echo "queue done $(date -u +%H:%M:%SZ)"
