#!/usr/bin/env python3
"""Print the stable content hash used by review.target_versions and run.protocol_sha256."""
import argparse
from pathlib import Path
from records import content_hash,parse
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('record')
parser.add_argument('--review-type',choices=['protocol','implementation','evidence','source'],default='evidence')
args=parser.parse_args()
path=Path(args.record)
print(content_hash(parse(path.read_text(),path.suffix=='.md'),args.review_type))
