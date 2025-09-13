#!/usr/bin/env python3
"""Analyze search engine selection metrics."""

import json
import os
from collections import defaultdict, Counter
from datetime import datetime, timedelta

def analyze_metrics(days=7):
    """Analyze search engine selection patterns."""
    metrics_file = os.path.join("src/websearch/search-metrics.jsonl")
    
    if not os.path.exists(metrics_file):
        print("No metrics file found. Start using the search to collect data.")
        return
    
    selections = []
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    
    try:
        with open(metrics_file, 'r') as f:
            for line in f:
                event = json.loads(line.strip())
                event_time = datetime.fromisoformat(event['timestamp'].replace('Z', '+00:00'))
                
                if event_time >= cutoff_date and event['event_type'] == 'url_selection':
                    selections.extend(event['selections'])
    
    except Exception as e:
        print(f"Error reading metrics: {e}")
        return
    
    if not selections:
        print("No selection data found in the specified time period.")
        return
    
    # Analyze engine performance
    engine_stats = Counter()
    search_sessions = set()
    
    for selection in selections:
        engine = selection['engine']
        search_id = selection['search_id']
        
        engine_stats[engine] += 1
        search_sessions.add(search_id)
    
    total_selections = sum(engine_stats.values())
    
    print(f"\n🔍 Search Engine Selection Analysis (Last {days} days)")
    print("=" * 50)
    print(f"Total URL selections: {total_selections}")
    print(f"Unique search sessions: {len(search_sessions)}")
    print(f"Average selections per search: {total_selections / max(len(search_sessions), 1):.1f}")
    
    print(f"\n📊 Engine Performance:")
    for engine, count in engine_stats.most_common():
        percentage = (count / total_selections) * 100
        print(f"  {engine.upper():<12}: {count:>3} selections ({percentage:>5.1f}%)")
    
    print(f"\n🏆 Winner: {engine_stats.most_common(1)[0][0].upper()} with {engine_stats.most_common(1)[0][1]} selections")

if __name__ == "__main__":
    analyze_metrics()
