import json, sys, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'core'))
import rebuild_cli

class StateMachineTests(unittest.TestCase):
    def test_valid_transition(self):
        self.assertEqual(rebuild_cli.transition('DISCOVER','evidence_ready')['to'],'EVIDENCE')
    def test_invalid_transition_rejected(self):
        with self.assertRaises(ValueError): rebuild_cli.transition('DISCOVER','decision_closed')
    def test_unknown_state_rejected(self):
        with self.assertRaises(ValueError): rebuild_cli.transition('MAGIC','evidence_ready')

class ProjectTests(unittest.TestCase):
    def test_example_project_valid(self):
        self.assertEqual(rebuild_cli.validate_project(ROOT/'examples/nanjiang_tea/project.json'),[])
    def test_missing_fields_detected(self):
        p=ROOT/'tests'/'_invalid_temp.json'
        try:
            p.write_text(json.dumps({'project_id':'x'}),encoding='utf-8')
            errors=rebuild_cli.validate_project(p)
            self.assertTrue(any('decision_question' in e for e in errors))
        finally:
            if p.exists(): p.unlink()

if __name__=='__main__': unittest.main()
