"""Property tests for portable hashes, bookkeeping, and schema/transition consistency."""

import copy
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from hypothesis import given, settings
from hypothesis import strategies as st
from record_helper import template
from records import content_hash, yaml
from validate_records import TRANSITIONS, history_errors

json_values = st.recursive(
    st.none()
    | st.booleans()
    | st.integers()
    | st.text()
    | st.floats(allow_nan=False, allow_infinity=False),
    lambda children: (
        st.lists(children, max_size=5) | st.dictionaries(st.text(), children, max_size=5)
    ),
    max_leaves=15,
)


class HashProperties(unittest.TestCase):
    @given(st.dictionaries(st.text(), json_values, max_size=8))
    def test_hash_survives_json_roundtrip_and_key_reordering(self, record):
        restored = json.loads(json.dumps(record))
        reordered = dict(reversed(list(restored.items())))
        self.assertEqual(content_hash(record), content_hash(reordered))

    @given(json_values, json_values)
    def test_bookkeeping_does_not_invalidate_evidence(self, status, links):
        before = {
            "kind": "claim",
            "statement": "Fixed scientific content",
            "scope": {"project": "fixture"},
        }
        after = {**before, "status": status, "references": links, "review_records": links}
        self.assertEqual(content_hash(before), content_hash(after))

    @given(st.text(min_size=1), st.text(min_size=1))
    def test_protocol_ignores_pinning_but_implementation_does_not(self, commit, checksum):
        before = {
            "kind": "experiment",
            "prediction": "Fixed",
            "implementation": {"file": "src/a.py", "commit": None, "patch": None},
            "configuration": {"file": "configs/a.json", "sha256": None},
        }
        after = copy.deepcopy(before)
        after["implementation"]["commit"] = commit
        after["configuration"]["sha256"] = checksum
        self.assertEqual(content_hash(before, "protocol"), content_hash(after, "protocol"))
        self.assertNotEqual(
            content_hash(before, "implementation"), content_hash(after, "implementation")
        )

    @given(st.sampled_from(sorted(TRANSITIONS)))
    def test_transition_graph_only_uses_schema_statuses(self, kind):
        schema = json.loads(
            (Path(__file__).resolve().parents[1] / "schemas" / f"{kind}.schema.json").read_text()
        )
        statuses = set(schema["properties"]["status"]["enum"])
        for before, after in TRANSITIONS[kind].items():
            self.assertIn(before, statuses)
            self.assertLessEqual(after, statuses)
        # Terminal execution evidence must never regain an editable state.
        if kind == "run":
            for terminal in ("completed", "failed", "cancelled"):
                self.assertFalse(TRANSITIONS[kind].get(terminal))


class HistoryProperties(unittest.TestCase):
    @settings(max_examples=12, deadline=None)
    @given(
        st.sampled_from(
            [
                (kind, before, middle, after)
                for kind in ("question", "task")
                for before, next_states in TRANSITIONS[kind].items()
                for middle in next_states
                for after in TRANSITIONS[kind].get(middle, set())
                if after != before and after not in next_states
            ]
        )
    )
    def test_committed_intermediate_gates_cannot_be_skipped(self, path):
        kind, before, middle, after = path
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            record = template(kind)
            folder = "questions" if kind == "question" else "tasks"
            target = root / f"research/{folder}/{record['id']}.yaml"
            target.parent.mkdir(parents=True)

            def save(status):
                record["status"] = status
                target.write_text(yaml.safe_dump(record, sort_keys=False))

            def git(*args):
                subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True)

            def commit():
                git("add", ".")
                git(
                    "-c",
                    "user.name=Property Fixture",
                    "-c",
                    "user.email=property@example.invalid",
                    "-c",
                    "commit.gpgsign=false",
                    "commit",
                    "-qm",
                    "record gate",
                )

            def errors():
                return history_errors(root, {record["id"]: (record, target)}, "HEAD")

            save(before)
            git("init", "-q")
            commit()
            save(after)
            self.assertTrue(any("forbidden transition" in error for error in errors()))
            save(middle)
            self.assertEqual(errors(), [])
            commit()
            save(after)
            self.assertEqual(errors(), [])
