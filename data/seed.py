"""Populate the DB with synthetic investigation cases.

Idempotent: exits without inserting if any case rows already exist.
Safe to run at Docker build time or on a pre-existing volume.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.database import init_db, get_connection
from datetime import datetime, timezone, timedelta
import random, string

random.seed(42)


def _now(offset_days: int = 0) -> str:
    dt = datetime.now(timezone.utc) - timedelta(days=offset_days)
    return dt.isoformat()


def _ref(prefix: str) -> str:
    return prefix + "-" + "".join(random.choices(string.ascii_uppercase + string.digits, k=6))


CASES = [
    ("Audit trail timestamps missing for batch release system", "LIMS-01", "audit_finding", "A.Reyes", 30),
    ("Shared login credential detected in QMS", "QMS-02", "user_access_anomaly", "J.Torres", 20),
    ("Raw data overwritten without original preservation", "ERP-03", "data_gap", "M.Colon", 15),
    ("Electronic records missing required metadata fields", "SCADA-04", "system_discrepancy", "A.Reyes", 10),
    ("Backup integrity check not performed for 90 days", "BACKUP-05", "audit_finding", "L.Rivera", 5),
]

ALCOA_ATTRS = [
    ("Attributable", True, "Actor field blank in 14 records"),
    ("Contemporaneous", True, "Timestamps recorded retroactively"),
    ("Original", False, "Original data preserved in read-only archive"),
    ("Accurate", True, "Values corrected without audit trail entry"),
    ("Complete", False, "All required fields populated"),
]

EVIDENCE = [
    ("audit_trail_review", "Reviewed 30-day audit trail export; 14 records lack actor attribution."),
    ("technical_metadata", "Server-side timestamp comparison shows 6-minute discrepancy."),
    ("access_log", "Shared credential login events identified in access log review."),
]

CAPAS = [
    ("corrective", "Enforce actor field as mandatory in LIMS configuration.", "A.Reyes", "2026-10-01"),
    ("preventive", "Implement automated timestamp integrity check on batch close.", "J.Torres", "2026-11-15"),
    ("corrective", "Revoke shared credentials and assign individual accounts.", "M.Colon", "2026-09-15"),
]


def seed():
    init_db()
    conn = get_connection()

    # Idempotency guard: skip all inserts if data already exists
    existing = conn.execute("SELECT COUNT(*) FROM cases").fetchone()[0]
    if existing > 0:
        print(f"Seed skipped: {existing} case(s) already present in database.")
        conn.close()
        return

    with conn:
        for title, system, signal_type, opener, days_ago in CASES:
            ref = _ref("DI")
            conn.execute(
                "INSERT INTO cases (case_ref,title,system,signal_type,status,opened_by,opened_at) VALUES (?,?,?,?,?,?,?)",
                (ref, title, system, signal_type, "investigation", opener, _now(days_ago))
            )

        case_ids = [r[0] for r in conn.execute("SELECT id FROM cases ORDER BY id").fetchall()]

        for cid in case_ids[:3]:
            for attr, gap, obs in ALCOA_ATTRS:
                conn.execute(
                    "INSERT INTO alcoa_gaps (case_id,attribute,gap_found,observation,assessed_by,assessed_at) VALUES (?,?,?,?,?,?)",
                    (cid, attr, int(gap), obs, "A.Reyes", _now(5))
                )

        for cid in case_ids[:2]:
            for ev_type, desc in EVIDENCE:
                conn.execute(
                    "INSERT INTO evidence_log (case_id,evidence_type,description,recorded_by,recorded_at) VALUES (?,?,?,?,?)",
                    (cid, ev_type, desc, "A.Reyes", _now(3))
                )

        for i, cid in enumerate(case_ids[:3]):
            a_type, desc, owner, due = CAPAS[i % len(CAPAS)]
            cref = _ref("CAPA")
            conn.execute(
                "INSERT INTO capas (case_id,capa_ref,action_type,description,owner,due_date,status,created_at) VALUES (?,?,?,?,?,?,?,?)",
                (cid, cref, a_type, desc, owner, due, "open", _now(2))
            )

        for cid in case_ids:
            conn.execute(
                "INSERT INTO audit_log (case_id,actor,action,detail,created_at) VALUES (?,?,?,?,?)",
                (cid, "seed_script", "case_seeded", "synthetic record", _now(0))
            )

    conn.close()
    print(f"Seeded {len(CASES)} synthetic cases with ALCOA+ gaps, evidence, CAPAs, and audit entries.")


if __name__ == "__main__":
    seed()
