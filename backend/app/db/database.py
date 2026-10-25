import sqlite3
import json
from datetime import datetime
from typing import List, Dict, Any, Optional
from ..core.config import DATABASE_PATH

def get_db_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. Claims Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS claims (
        claim_id TEXT PRIMARY KEY,
        status TEXT NOT NULL,
        claim_type TEXT NOT NULL,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        state_json TEXT NOT NULL,
        trace_id TEXT,
        trace_url TEXT
    );
    """)
    try:
        cursor.execute("ALTER TABLE claims ADD COLUMN trace_id TEXT;")
    except Exception:
        pass
    try:
        cursor.execute("ALTER TABLE claims ADD COLUMN trace_url TEXT;")
    except Exception:
        pass


    # 2. Agent Runs Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS agent_runs (
        run_id INTEGER PRIMARY KEY AUTOINCREMENT,
        claim_id TEXT NOT NULL,
        agent_name TEXT NOT NULL,
        input_json TEXT,
        output_json TEXT,
        status TEXT NOT NULL,
        duration_ms REAL,
        created_at TEXT NOT NULL,
        FOREIGN KEY (claim_id) REFERENCES claims(claim_id)
    );
    """)

    # 3. Audit Events Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS audit_events (
        event_id INTEGER PRIMARY KEY AUTOINCREMENT,
        claim_id TEXT NOT NULL,
        stage TEXT NOT NULL,
        event_type TEXT NOT NULL,
        route_reason TEXT NOT NULL,
        evidence_json TEXT,
        created_at TEXT NOT NULL,
        FOREIGN KEY (claim_id) REFERENCES claims(claim_id)
    );
    """)

    # 4. Review Tasks Table (HITL)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS review_tasks (
        task_id TEXT PRIMARY KEY,
        claim_id TEXT NOT NULL,
        task_type TEXT NOT NULL,
        priority TEXT NOT NULL,
        status TEXT NOT NULL,
        details_json TEXT NOT NULL,
        decision_note TEXT,
        created_at TEXT NOT NULL,
        resolved_at TEXT,
        FOREIGN KEY (claim_id) REFERENCES claims(claim_id)
    );
    """)

    # 5. Simulated Ledger (Idempotent payout registry)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS simulated_ledger (
        txn_id TEXT PRIMARY KEY,
        claim_id TEXT UNIQUE NOT NULL,
        amount REAL NOT NULL,
        recipient TEXT NOT NULL,
        status TEXT NOT NULL,
        created_at TEXT NOT NULL,
        FOREIGN KEY (claim_id) REFERENCES claims(claim_id)
    );
    """)

    # 6. Policy Chunks Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS policy_chunks (
        chunk_id TEXT PRIMARY KEY,
        policy_no TEXT NOT NULL,
        source_file TEXT NOT NULL,
        section_title TEXT NOT NULL,
        page_number INTEGER NOT NULL,
        chunk_text TEXT NOT NULL
    );
    """)

    # 7. Policy Chunks FTS5 Virtual Table
    cursor.execute("""
    CREATE VIRTUAL TABLE IF NOT EXISTS policy_chunks_fts USING fts5(
        chunk_id UNINDEXED,
        policy_no,
        section_title,
        page_number UNINDEXED,
        chunk_text
    );
    """)

    conn.commit()
    conn.close()
    
    seed_knowledge_data()

def seed_knowledge_data():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) as count FROM policy_chunks;")
    if cursor.fetchone()["count"] > 0:
        conn.close()
        return

    sample_chunks = [
        {
            "chunk_id": "CHK-001",
            "policy_no": "POL-AUTO-99201",
            "source_file": "comprehensive_motor_policy_2026.pdf",
            "section_title": "Section 1.1: Policy Period & Limits",
            "page_number": 2,
            "chunk_text": "This Comprehensive Motor Vehicle Policy is valid for active policyholders from 2026-01-01 to 2027-01-01. Maximum single incident coverage limit is $50,000 for direct property collision damage."
        },
        {
            "chunk_id": "CHK-002",
            "policy_no": "POL-AUTO-99201",
            "source_file": "comprehensive_motor_policy_2026.pdf",
            "section_title": "Section 4.2: Collision and Comprehensive Coverage",
            "page_number": 5,
            "chunk_text": "Coverage applies to sudden and accidental physical damage caused by collision with another vehicle or stationary object, including rear collision, front impact, and side impact. Standard policyholder deductible is $500.00 per collision event."
        },
        {
            "chunk_id": "CHK-003",
            "policy_no": "POL-AUTO-99201",
            "source_file": "comprehensive_motor_policy_2026.pdf",
            "section_title": "Section 5.1: Repair Valuation & Labor Rates",
            "page_number": 8,
            "chunk_text": "Approved repair estimates are benchmarked against certified OEM parts catalogs and regional labor rates. Standard certified collision labor rate is capped at $85.00/hour. Vehicle components with normal wear are subject to standard age depreciation schedules."
        },
        {
            "chunk_id": "CHK-004",
            "policy_no": "POL-AUTO-99201",
            "source_file": "comprehensive_motor_policy_2026.pdf",
            "section_title": "Section 8.3: General Exclusions - Racing & Unlawful Operation",
            "page_number": 12,
            "chunk_text": "Exclusions: No coverage is provided for loss or damage sustained while participating in any organized racing, speed contest, track day, drifting exhibition, or commercial ride-sharing without prior endorsement. Claims arising from excluded activities shall be subject to coverage exception review."
        },
        {
            "chunk_id": "CHK-005",
            "policy_no": "POL-AUTO-88104",
            "source_file": "standard_collision_policy_2026.pdf",
            "section_title": "Section 3.1: High Value Vehicle Terms & Deductible",
            "page_number": 4,
            "chunk_text": "Policy POL-AUTO-88104 provides luxury and performance vehicle coverage with an agreed deductible of $1,000.00. Estimates exceeding $10,000.00 require specialized OEM certified facility inspection and human adjuster review prior to final disbursement."
        },
        {
            "chunk_id": "CHK-006",
            "policy_no": "POL-AUTO-77002",
            "source_file": "expired_policy_notice.pdf",
            "section_title": "Section 2.4: Policy Lapse Notice",
            "page_number": 1,
            "chunk_text": "Notice of Policy Lapse: Policy POL-AUTO-77002 lapsed on 2025-12-31 due to non-payment of renewal premium. No coverage exists for incidents occurring after the lapse date. Any submitted claim must be referred for coverage denial review."
        }
    ]

    for chunk in sample_chunks:
        cursor.execute("""
        INSERT INTO policy_chunks (chunk_id, policy_no, source_file, section_title, page_number, chunk_text)
        VALUES (?, ?, ?, ?, ?, ?);
        """, (chunk["chunk_id"], chunk["policy_no"], chunk["source_file"], chunk["section_title"], chunk["page_number"], chunk["chunk_text"]))
        
        cursor.execute("""
        INSERT INTO policy_chunks_fts (chunk_id, policy_no, section_title, page_number, chunk_text)
        VALUES (?, ?, ?, ?, ?);
        """, (chunk["chunk_id"], chunk["policy_no"], chunk["section_title"], chunk["page_number"], chunk["chunk_text"]))

    conn.commit()
    conn.close()

def search_policy_clauses(query: str, policy_no: Optional[str] = None, limit: int = 5) -> List[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Clean query for FTS5 MATCH syntax (words separated by OR or simple terms)
    terms = [w.strip() for w in query.replace("-", " ").replace(":", " ").replace(",", " ").split() if len(w.strip()) > 2]
    if not terms:
        conn.close()
        return []
    
    match_query = " OR ".join(f'"{t}"' for t in terms[:6])
    
    if policy_no:
        cursor.execute("""
        SELECT chunk_id, policy_no, section_title, page_number, chunk_text, rank
        FROM policy_chunks_fts
        WHERE policy_chunks_fts MATCH ? AND policy_no = ?
        ORDER BY rank
        LIMIT ?;
        """, (match_query, policy_no, limit))
    else:
        cursor.execute("""
        SELECT chunk_id, policy_no, section_title, page_number, chunk_text, rank
        FROM policy_chunks_fts
        WHERE policy_chunks_fts MATCH ?
        ORDER BY rank
        LIMIT ?;
        """, (match_query, limit))
        
    rows = cursor.fetchall()
    results = [dict(row) for row in rows]
    conn.close()
    return results
