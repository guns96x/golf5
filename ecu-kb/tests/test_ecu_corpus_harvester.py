import importlib.util
import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
TOOL_PATH = REPO / "tools" / "ecu_corpus_harvester.py"

spec = importlib.util.spec_from_file_location("ecu_corpus_harvester", TOOL_PATH)
harvester = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(harvester)


class CorpusClassifierTests(unittest.TestCase):
    def test_exact_by_part_calibration_and_version(self):
        cls, score, reasons = harvester.classify({
            "ecu_family": "EDC16U34",
            "vag_part_number": "03G906021QJ",
            "vag_sw_version": "1984",
            "calibration_id": "391847",
        })
        self.assertEqual(cls, "EXACT")
        self.assertGreaterEqual(score, 70)
        self.assertIn("VAG part number exact", reasons)

    def test_same_part_sibling_is_not_exact(self):
        cls, score, _ = harvester.classify({
            "ecu_family": "EDC16U34",
            "vag_part_number": "03G906021QJ",
            "vag_sw_version": "1340",
            "calibration_id": "389289",
            "project_code": "P447 HAXN",
        })
        self.assertEqual(cls, "SAME_HW_SIBLING")
        self.assertLess(score, 100)

    def test_same_project_family(self):
        cls, score, _ = harvester.classify({
            "ecu_family": "EDC16U34",
            "vag_part_number": "03G906021RN",
            "vag_sw_version": "1989",
            "calibration_id": "391834",
            "project_code": "P447 HAXN",
        })
        self.assertEqual(cls, "SAME_PROJECT_FAMILY")
        self.assertGreaterEqual(score, 45)

    def test_filename_parser_extracts_exact_target_tuple(self):
        meta = harvester.extract_filename_metadata(Path(
            "03G906021QJ_1984_391847_P447_HAXN_EDC16U34_3.42.a2l"
        ))
        self.assertEqual(meta["vag_part_number"], "03G906021QJ")
        self.assertEqual(meta["vag_sw_version"], "1984")
        self.assertEqual(meta["calibration_id"], "391847")
        self.assertEqual(meta["project_code"], "P447 HAXN")
        self.assertEqual(meta["ecu_family"], "EDC16U34")
        self.assertEqual(meta["ecu_variant"], "EDC16U34-3.42")

    def test_wrong_family_never_exact(self):
        cls, score, _ = harvester.classify({
            "ecu_family": "EDC16C34",
            "vag_part_number": "03G906021QJ",
            "calibration_id": "391847",
        })
        self.assertEqual(cls, "STRUCTURAL_ANALOG")
        self.assertLess(score, 50)


class CorpusDbTests(unittest.TestCase):
    def test_seed_and_local_scan(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            db = root / "kb.sqlite3"
            c = harvester.connect(db)
            try:
                harvester.ensure_schema(c)
                ns, na = harvester.load_seeds(c, harvester.DEFAULT_SEEDS)
                self.assertGreaterEqual(ns, 5)
                self.assertGreaterEqual(na, 10)

                report = harvester.report(c)
                exact = [x for x in report["artifacts"] if x["match_class"] == "EXACT"]
                self.assertTrue(any("391847" in x["name"] for x in exact))

                corpus = root / "local"
                corpus.mkdir()
                sample = corpus / "my_EDC16U34_03G906021QJ.bin"
                sample.write_bytes(
                    b"\x00" * 64
                    + b"EDC16U34\x00"
                    + b"03G906021QJ\x00"
                    + b"1037391847\x00"
                    + b"391847\x00"
                    + b"P447 HAXN\x00"
                    + b"BLS\x00"
                )
                n = harvester.scan_local(c, corpus)
                self.assertEqual(n, 1)

                row = c.execute(
                    """
                    SELECT a.sha256,a.access_state,m.match_class,m.score
                    FROM corpus_artifacts a
                    JOIN corpus_matches m ON m.artifact_id=a.id
                    WHERE a.name=?
                    """,
                    (sample.name,),
                ).fetchone()
                self.assertIsNotNone(row)
                self.assertEqual(row["access_state"], "AVAILABLE_LOCAL")
                self.assertEqual(row["match_class"], "EXACT")
                self.assertEqual(len(row["sha256"]), 64)
            finally:
                c.close()

    def test_seed_refresh_does_not_erase_verified_local_state(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            db = root / "kb.sqlite3"
            c = harvester.connect(db)
            try:
                harvester.ensure_schema(c)
                harvester.load_seeds(c, harvester.DEFAULT_SEEDS)
                row = c.execute(
                    """
                    SELECT a.id
                    FROM corpus_artifacts a
                    JOIN corpus_sources s ON s.id=a.source_id
                    WHERE s.source_key='tunepad_catalog'
                      AND a.name LIKE '%391847%'
                    LIMIT 1
                    """
                ).fetchone()
                self.assertIsNotNone(row)

                local = root / "03G906021QJ_1984_391847_full_stock.bin"
                local.write_bytes(b"EDC16U34 03G906021QJ 391847")
                self.assertEqual(harvester.cmd_verify_local(c, int(row["id"]), local), 0)

                before = c.execute(
                    "SELECT sha256,access_state,identity_state,local_rel_path FROM corpus_artifacts WHERE id=?",
                    (int(row["id"]),),
                ).fetchone()
                self.assertEqual(before["access_state"], "VERIFIED_LOCAL")
                self.assertTrue(before["sha256"])

                harvester.load_seeds(c, harvester.DEFAULT_SEEDS)
                after = c.execute(
                    "SELECT sha256,access_state,identity_state,local_rel_path FROM corpus_artifacts WHERE id=?",
                    (int(row["id"]),),
                ).fetchone()
                self.assertEqual(after["sha256"], before["sha256"])
                self.assertEqual(after["access_state"], "VERIFIED_LOCAL")
                self.assertEqual(after["identity_state"], before["identity_state"])
                self.assertEqual(after["local_rel_path"], before["local_rel_path"])
            finally:
                c.close()

    def test_project_a2l_hash_becomes_project_verified_not_self_hash_matched(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            db = root / "kb.sqlite3"
            c = harvester.connect(db)
            try:
                harvester.ensure_schema(c)
                corpus = root / "local"
                corpus.mkdir()
                sample = corpus / "03G906021QJ_1984_391847_P447_HAXN_EDC16U34_3.42.a2l"
                sample.write_bytes(b"/begin PROJECT P447 HAXN EDC16U34 BLS")
                digest = harvester.sha256_file(sample)

                c.execute(
                    """
                    INSERT INTO a2l_objects(
                        sw_number,name,description,obj_type,kind,address,
                        record_layout,func_group,a2l_sha256
                    ) VALUES(?,?,?,?,?,?,?,?,?)
                    """,
                    (
                        "1037391847","PCR_test","test","MAP",
                        "CHARACTERISTIC","0x1","RL","PCR",digest,
                    ),
                )
                c.commit()

                harvester.scan_local(c, corpus)
                row = c.execute(
                    "SELECT id FROM corpus_artifacts WHERE name=?",
                    (sample.name,),
                ).fetchone()
                self.assertIsNotNone(row)

                self.assertEqual(
                    harvester.cmd_verify_local(c, int(row["id"]), sample), 0
                )
                checked = c.execute(
                    """
                    SELECT a.identity_state,a.bosch_sw_number,m.match_class,m.score
                    FROM corpus_artifacts a
                    JOIN corpus_matches m ON m.artifact_id=a.id
                    WHERE a.id=?
                    """,
                    (int(row["id"]),),
                ).fetchone()
                self.assertEqual(checked["identity_state"], "PROJECT_VERIFIED")
                self.assertEqual(checked["bosch_sw_number"], "1037391847")
                self.assertEqual(checked["match_class"], "EXACT")
                self.assertGreaterEqual(checked["score"], 90)
            finally:
                c.close()


if __name__ == "__main__":
    unittest.main()
