#!/usr/bin/env python3
"""Analyze search engine selection metrics and compare with LLM responses."""

import json
import sys
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path


def analyze_metrics(days=7):
    """Analyze search responses vs LLM selections."""
    metrics_file = Path("src/websearch/search-metrics.jsonl")
    
    if not metrics_file.exists():
        print("No metrics file found. Start using the search to collect data.")
        return
    
    cutoff_date = datetime.now().replace(tzinfo=None) - timedelta(days=days)
    
    search_responses = []
    url_selections = []
    
    # Parse metrics file
    with open(metrics_file, 'r') as f:
        for line in f:
            try:
                data = json.loads(line.strip())
                timestamp = datetime.fromisoformat(data['timestamp'].replace('Z', '').replace('+00:00', ''))
                
                if timestamp < cutoff_date:
                    continue
                
                if data.get('event_type') == 'search_response':
                    search_responses.append(data)
                elif data.get('event_type') == 'url_selection':
                    url_selections.append(data)
                    
            except (json.JSONDecodeError, KeyError, ValueError):
                continue
    
    print(f"\n🔍 Search Response vs LLM Selection Analysis (Last {days} days)")
    print("=" * 60)
    
    if not search_responses and not url_selections:
        print("No data found in the specified time range.")
        return
    
    # Analyze search responses
    if search_responses:
        print(f"\n📤 Search Responses Sent to LLM: {len(search_responses)}")
        
        total_results_sent = sum(r['total_results'] for r in search_responses)
        engine_sent = defaultdict(int)
        
        for response in search_responses:
            for engine, count in response['engine_distribution'].items():
                engine_sent[engine] += count
        
        print(f"Total results sent to LLM: {total_results_sent}")
        print("Engine distribution in responses:")
        for engine, count in sorted(engine_sent.items()):
            percentage = (count / total_results_sent * 100) if total_results_sent > 0 else 0
            print(f"  {engine.upper():12}: {count:3d} results ({percentage:5.1f}%)")
    
    # Analyze URL selections
    if url_selections:
        print(f"\n📥 LLM URL Selections: {len(url_selections)}")
        
        total_selections = 0
        engine_selected = defaultdict(int)
        
        for selection in url_selections:
            for sel in selection.get('selections', []):
                total_selections += 1
                engine_selected[sel['engine']] += 1
        
        print(f"Total URLs selected by LLM: {total_selections}")
        print("Engine distribution in selections:")
        for engine, count in sorted(engine_selected.items()):
            percentage = (count / total_selections * 100) if total_selections > 0 else 0
            print(f"  {engine.upper():12}: {count:3d} selections ({percentage:5.1f}%)")
    
    # Compare if we have both
    if search_responses and url_selections:
        print(f"\n📊 Response vs Selection Comparison:")
        print("-" * 40)
        
        for engine in set(list(engine_sent.keys()) + list(engine_selected.keys())):
            sent = engine_sent.get(engine, 0)
            selected = engine_selected.get(engine, 0)
            
            sent_pct = (sent / total_results_sent * 100) if total_results_sent > 0 else 0
            selected_pct = (selected / total_selections * 100) if total_selections > 0 else 0
            
            print(f"{engine.upper():12}: {sent_pct:5.1f}% sent → {selected_pct:5.1f}% selected")
        
        # Selection rate
        if total_results_sent > 0:
            selection_rate = (total_selections / total_results_sent * 100)
            print(f"\nOverall selection rate: {selection_rate:.1f}% ({total_selections}/{total_results_sent})")


if __name__ == "__main__":
    days = int(sys.argv[1]) if len(sys.argv) > 1 else 7
    analyze_metrics(days)
