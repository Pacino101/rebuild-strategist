#!/usr/bin/env python3
"""Minimal stdlib validator and deterministic REBUILD state-machine CLI."""
import argparse, json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
STATE_FILE = ROOT / "core" / "state_machine.json"

def load_json(path):
    with open(path, encoding="utf-8") as f: return json.load(f)

def transition(state, event):
    machine = load_json(STATE_FILE)
    if state not in machine["states"]:
        raise ValueError(f"Unknown state: {state}")
    nxt = machine["transitions"].get(state, {}).get(event)
    if not nxt:
        raise ValueError(f"Transition not allowed: {state} + {event}")
    return {"from": state, "event": event, "to": nxt}

def validate_project(path):
    data = load_json(path)
    errors=[]
    for field in ("project_id", "name", "decision_question", "current_state", "goals", "constraints"):
        if field not in data: errors.append(f"missing required field: {field}")
    machine=load_json(STATE_FILE)
    if data.get("current_state") not in machine["states"]: errors.append("current_state is not a known state")
    if not isinstance(data.get("goals", []), list): errors.append("goals must be an array")
    if not isinstance(data.get("constraints", []), list): errors.append("constraints must be an array")
    return errors

def main():
    p=argparse.ArgumentParser(description="REBUILD V3.2 local validation tools")
    sub=p.add_subparsers(dest="cmd", required=True)
    v=sub.add_parser("validate"); v.add_argument("project")
    t=sub.add_parser("transition"); t.add_argument("--state", required=True); t.add_argument("--event", required=True)
    a=p.parse_args()
    try:
        if a.cmd=="validate":
            errors=validate_project(a.project)
            if errors:
                print(json.dumps({"valid":False,"errors":errors},ensure_ascii=False,indent=2)); return 1
            print(json.dumps({"valid":True,"project":a.project},ensure_ascii=False,indent=2)); return 0
        print(json.dumps(transition(a.state,a.event),ensure_ascii=False,indent=2)); return 0
    except (ValueError, OSError, json.JSONDecodeError) as e:
        print(json.dumps({"error":str(e)},ensure_ascii=False,indent=2),file=sys.stderr); return 2
if __name__=="__main__": sys.exit(main())
