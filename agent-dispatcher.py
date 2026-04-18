#!/usr/bin/env python3
"""Agent Dispatcher - Autonomous pull-based dispatcher for agentneo"""

import subprocess
import json
import sys
from typing import Optional, Dict, Any, List, Tuple

def run_gh(cmd: str) -> Tuple[str, str, int]:
    """Run GitHub CLI command"""
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return result.stdout, result.stderr, result.returncode

def query_board() -> Dict:
    """Query board using safe GraphQL pattern"""
    query = """query {
  repository(owner: "thewillhuang", name: "agentneo") {
    projectsV2(first: 1) {
      nodes {
        items(first: 100) {
          nodes {
            id
            content {
              __typename
              ... on Issue { number title state }}
            fieldValues(first: 10) {
              nodes {
                ... on ProjectV2ItemFieldSingleSelectValue {
                  name
                  field {
                    ... on ProjectV2SingleSelectField {
                      name
                    }
                  }
                }
              }
            }
          }
        }
      }
    }
  }
}"""
    cmd = f'gh api graphql -f \'query={query}\''
    stdout, stderr, rc = run_gh(cmd)
    if rc != 0:
        print(f"[ERROR] GraphQL query failed: {stderr}", file=sys.stderr)
        return {}
    try:
        return json.loads(stdout)
    except json.JSONDecodeError as e:
        print(f"[ERROR] JSON parse failed: {e}", file=sys.stderr)
        return {}

def total_count(data: Dict) -> int:
    """Safely get total count"""
    try:
        total = data.get('data', {}).get('repository', {}).get('projectsV2', {}).get('nodes', [{}])[0].get('items', {}).get('totalCount', 0)
        return int(total) if total else 0
    except (KeyError, IndexError, TypeError):
        return 0

def in_progress_count(data: Dict) -> int:
    """Count In Progress items"""
    items = data.get('data', {}).get('repository', {}).get('projectsV2', {}).get('nodes', [{}])[0].get('items', {}).get('nodes', [])
    count = 0
    for item in items:
        for field in item.get('fieldValues', {}).get('nodes', []):
            if field.get('name') == 'Status':
                if field.get('field', {}).get('name', '') == 'In progress':
                    count += 1
                break
    return count

def existing_pr_for_issue(issue_num: int) -> Optional[int]:
    """Check for existing PR that closes this issue"""
    stdout, _, _ = run_gh(f'gh pr list --state open --json number,title,body')
    try:
        prs = json.loads(stdout)
        for pr in prs:
            body = (pr.get('body') or '').lower()
            if f'closes #{issue_num}' in body or f'fixes #{issue_num}' in body:
                return pr['number']
    except:
        pass
    return None

def get_ready_items(data: Dict) -> List[Dict]:
    """Get Ready items sorted by priority"""
    items = data.get('data', {}).get('repository', {}).get('projectsV2', {}).get('nodes', [{}])[0].get('items', {}).get('nodes', [])
    
    ready = []
    for item in items:
        content = item.get('content', {})
        if not content or content.get('__typename') not in ['Issue', 'PullRequest']:
            continue
        
        fields = item.get('fieldValues', {}).get('nodes', [])
        status_val = ''
        priority = 'P2'
        
        for field in fields:
            if field.get('name') == 'Status':
                status_val = field.get('field', {}).get('name', '')
            elif field.get('name') == 'Priority':
                priority = field.get('field', {}).get('name', 'P2')
        
        if status_val == 'Ready':
            ready.append({
                'number': content.get('number'),
                'title': content.get('title'),
                'type': content.get('__typename'),
                'priority': priority
            })
    
    priority_order = {'P0': 0, 'P1': 1, 'P2': 2}
    ready.sort(key=lambda x: priority_order.get(x.get('priority', 'P2'), 2))
    return ready

def claim_issue(issue_number: int) -> bool:
    """Claim an issue by setting status to 'In progress'"""
    cmd = f'gh api graphql -f \'mutation={{ updateProjectV2ItemFieldValue(input: {{projectId: "PVT_kwHOAHgLT84BUsgT", itemId: "{issue_number}", fieldId: "PVTSSF_lAHOAHgLT84BUsgTzhCINu8", value: {{singleSelectOptionId: "47fc9ee4"}}}}}\'''
    stdout, stderr, rc = run_gh(cmd)
    return rc == 0

def main():
    print("[agent: agent-dispatcher | process: heartbeat]")
    
    # Check WIP limit
    wip = in_progress_count(query_board())
    print(f"[CHECK] In Progress: {wip}/3")
    if wip >= 3:
        print("[IDLE]")
        return
    
    # Get board data and ready items
    data = query_board()
    if not data:
        return
    
    ready_items = get_ready_items(data)
    if not ready_items:
        print("[IDLE]")
        return
    
    # Claim highest priority item
    for item in ready_items:
        num = item['number']
        pr_num = existing_pr_for_issue(num)
        if pr_num:
            print(f"[SKIP] #{num} already has PR #{pr_num}")
            continue
        
        print(f"[CLAIM] Claiming #{num}: {item['title']}")
        if claim_issue(num):
            print(f"[SUCCESS] Claimed #{num}")
        else:
            print(f"[FAIL] Failed to claim #{num}")
        break

if __name__ == '__main__':
    main()