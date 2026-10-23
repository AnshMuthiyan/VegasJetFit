#!/usr/bin/env python3
"""Verify delivered bytes; does not establish scientific correctness."""
from pathlib import Path
import csv,hashlib
root=Path(__file__).resolve().parent
rows=list(csv.DictReader((root/'BUNDLE_SHA256.csv').open()))
for row in rows:
 p=root/row['path']
 assert p.stat().st_size==int(row['bytes']),p
 assert hashlib.sha256(p.read_bytes()).hexdigest()==row['sha256'],p
print(f'PASS: {len(rows)} delivered file sizes and SHA-256 values')
