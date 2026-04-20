#!/usr/bin/env python3
import sys, re
from pathlib import Path
from statistics import mean, variance, stdev
from datetime import datetime
import argparse

class NewickParser:
    def __init__(self, nwk):
        self.s = nwk.strip().rstrip(';')
        self.root = self._parse([0])
    
    def _parse(self, pos):
        node = {'children': [], 'bl': 0.0}
        if pos[0] < len(self.s) and self.s[pos[0]] == '(':
            pos[0] += 1
            while pos[0] < len(self.s) and self.s[pos[0]] != ')':
                if self.s[pos[0]] == ',':
                    pos[0] += 1
                node['children'].append(self._parse(pos))
            pos[0] += 1
        m = re.match(r'[^:,();]*(?::([0-9.eE-]+))?', self.s[pos[0]:])
        if m:
            if m.group(1): node['bl'] = float(m.group(1))
            pos[0] += len(m.group(0))
        return node
    
    def leaf_depths(self):
        depths = []
        def collect(n, d):
            d += n['bl']
            if not n['children']: depths.append(d)
            else: [collect(c, d) for c in n['children']]
        collect(self.root, 0.0)
        return depths
    
    def stats(self):
        depths = self.leaf_depths()
        return {
            'leaves': len(depths), 'max': max(depths), 'min': min(depths),
            'mean': mean(depths), 'var': variance(depths) if len(depths) > 1 else 0,
            'sd': stdev(depths) if len(depths) > 1 else 0
        } if depths else {'leaves': 0, 'max': 0, 'min': 0, 'mean': 0, 'var': 0, 'sd': 0}


def analyze_file(fpath):
    try:
        stats = NewickParser(Path(fpath).read_text()).stats()
        return {'file': fpath, 'stats': stats}
    except Exception as e:
        return {'file': fpath, 'error': str(e)}

def analyze_dir(dpath):
    p = Path(dpath)
    files = sorted(p.glob('*.treefile'))
    return [analyze_file(f) for f in files] if files else []

def print_results(results):
    print("\n" + "="*80 + "\nTREE DEPTH ANALYSIS\n" + "="*80 + "\n")
    stats_list = []
    for r in results:
        if 'stats' in r:
            fpath = Path(r['file'])
            s = r['stats']
            stats_list.append(s)
            v_match = re.search(r'/v_(\d+)/', str(fpath))
            v_num = v_match.group(1) if v_match else "unknown"
            mtime = datetime.fromtimestamp(fpath.stat().st_mtime).strftime('%Y-%m-%d %H:%M:%S')
            print(f"{fpath.name}:")
            print(f"  Version: v_{v_num} | Created: {mtime}")
            print(f"  Leaves: {s['leaves']} | Max: {s['max']:.6f} | Min: {s['min']:.6f}")
            print(f"  Mean: {s['mean']:.6f} | Variance: {s['var']:.12f} | StdDev: {s['sd']:.12f}\n")
        else:
            print(f"ERROR {r['file']}: {r['error']}\n")
    
    if len(stats_list) > 1:
        print("-"*80)
        print(f"Aggregate ({len(stats_list)} trees): Mean of means = {mean([s['mean'] for s in stats_list]):.6f}\n")
    print("Best file for analysis: *.treefile (Newick with branch lengths)")

if __name__ == '__main__':
    p = argparse.ArgumentParser(description='IQ-TREE depth statistics')
    p.add_argument('target', help='Tree file, directory, or glob pattern')
    p.add_argument('-v', '--verbose', action='store_true')
    args = p.parse_args()
    
    from glob import glob
    paths = sorted(glob(args.target)) if '*' in args.target else [args.target]
    results = []
    
    for tp in paths:
        tp = Path(tp)
        if tp.is_file() and tp.suffix == '.treefile':
            results.append(analyze_file(tp))
        elif tp.is_dir():
            results.extend(analyze_dir(tp))
    
    print_results(results)
