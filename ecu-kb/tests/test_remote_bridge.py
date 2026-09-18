import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))

import remote_bridge
from specialist import DieselSpecialist


class RemoteBridgeTests(unittest.TestCase):
    def make_db(self, root: Path) -> Path:
        db = root / "kb.sqlite3"
        c = sqlite3.connect(db)
        c.executescript((HERE / "schema.sql").read_text(encoding="utf-8"))

        sid = c.execute(
            """INSERT INTO sources(title,obtainability,tier,authority,applicability)
               VALUES('OEM test','HAVE_LOCAL','A',5,5)"""
        ).lastrowid
        did = c.execute(
            """INSERT INTO documents(source_id,rel_path,sha256,bytes,pages,text_layer,chars_per_page)
               VALUES(?,?,?,?,?,?,?)""",
            (sid, "oem/test.txt", "a" * 64, 100, 1, "GOOD", 1000),
        ).lastrowid
        cid = c.execute(
            """INSERT INTO chunks(document_id,ordinal,page_from,page_to,content,n_chars)
               VALUES(?,?,?,?,?,?)""",
            (did, 0, 1, 1, "Charge pressure controller evidence text.", 41),
        ).lastrowid

        claim_id = c.execute(
            """INSERT INTO claims(
                statement,evidence_kind,verification_state,quantity_kind,unit,
                ecu_family,ecu_variant,sw_number,engine_code,confidence,source_class
               ) VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
            (
                "PCR_rBPCtlBas_MAP test claim",
                "OEM_DOCUMENTED",
                "corroborated",
                "calibration",
                "mbar",
                "EDC16",
                "EDC16U34",
                "1037391847",
                "BLS",
                0.9,
                "document_citation",
            ),
        ).lastrowid
        c.execute(
            """INSERT INTO citations(claim_id,chunk_id,doc_sha256,locator,quote,verified_at)
               VALUES(?,?,?,?,?,datetime('now'))""",
            (claim_id, cid, "a" * 64, "p.1", "Charge pressure controller evidence text."),
        )
        c.execute(
            """INSERT INTO gaps(question,why_needed,priority,status,needed_source)
               VALUES('Need compressor map','physical limit',1,'OPEN','matching component source')"""
        )
        c.execute(
            """INSERT INTO a2l_objects(
                sw_number,name,description,obj_type,kind,address,record_layout,func_group,a2l_sha256
               ) VALUES(?,?,?,?,?,?,?,?,?)""",
            (
                "1037391847",
                "PCR_rBPCtlBas_MAP",
                "test map",
                "MAP",
                "CHARACTERISTIC",
                "0x1E0000",
                "RL",
                "PCR",
                "b" * 64,
            ),
        )
        c.commit()
        c.close()
        return db

    def test_export_and_verify(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            db = self.make_db(root)
            out = root / "remote"

            rc = remote_bridge.export_snapshot(db, out, skip_check=True)
            self.assertEqual(rc, 0)

            # Test fixture uses a temporary DB, so kb.py check cannot target it.
            # Promote only the fixture manifest to PASSED before testing the
            # consumer-side integrity contract.
            manifest_path = out / "manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["integrity"]["kb_check"] = "PASSED"
            manifest_path.write_text(
                json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            self.assertEqual(remote_bridge.verify_snapshot(out), 0)

            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            claims = json.loads((out / "claims.json").read_text(encoding="utf-8"))
            retractions = json.loads((out / "retractions.json").read_text(encoding="utf-8"))
            gaps = json.loads((out / "gaps.json").read_text(encoding="utf-8"))
            a2l = json.loads((out / "a2l" / "PCR.json").read_text(encoding="utf-8"))

            self.assertEqual(manifest["snapshot_state"], "CANONICAL_DB_EXPORT")
            self.assertFalse(manifest["privacy_boundary"]["raw_corpus_exported"])
            self.assertEqual(claims["claims"][0]["epistemic_role"], "support")
            self.assertEqual(claims["claims"][0]["citations"][0]["locator"], "p.1")
            self.assertEqual(retractions["retractions"], [])
            self.assertEqual(gaps["gaps"][0]["status"], "OPEN")
            self.assertEqual(a2l["objects"][0]["name"], "PCR_rBPCtlBas_MAP")

            spec = DieselSpecialist(db_path=root / "missing.sqlite3", snapshot_dir=out)
            self.assertEqual(spec.mode, "snapshot")
            report = spec.consult("PCR_rBPCtlBas_MAP")
            self.assertIn("PCR_rBPCtlBas_MAP", report)
            self.assertIn("PCR_rBPCtlBas_MAP test claim", report)

    def test_epistemic_role(self):
        self.assertEqual(
            remote_bridge.epistemic_role({
                "verification_state": "corroborated",
                "evidence_kind": "MEASURED",
            }),
            "support",
        )
        self.assertEqual(
            remote_bridge.epistemic_role({
                "verification_state": "raw",
                "evidence_kind": "MEASURED",
            }),
            "context",
        )
        self.assertEqual(
            remote_bridge.epistemic_role({
                "verification_state": "contradicted",
                "evidence_kind": "CALCULATED",
            }),
            "negative",
        )


if __name__ == "__main__":
    unittest.main()
