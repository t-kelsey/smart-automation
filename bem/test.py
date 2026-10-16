"""Run the pipeline on 5 random input files. Dry run: JSON is written, nothing is POSTed."""

import random
from pathlib import Path

from main import input_files, process

files = list(input_files([Path("../data/HKBoreholeChallenge_Data_BFH2026/BoreholeData")]))
sample = random.sample(files, 5)
print("sample:", [f.name for f in sample])

for path in sample:
    for borehole in process(path, api=None):
        print(f"{path.name}: borehole={borehole.borehole_id} chars={len(borehole.raw_markdown)}")
