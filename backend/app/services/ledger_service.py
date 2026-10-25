import uuid
from datetime import datetime, timezone
from typing import Dict, Any
from ..db.database import get_db_connection

class LedgerService:
    @staticmethod
    def disburse_settlement(claim_id: str, amount: float, recipient: str) -> Dict[str, Any]:
        """
        Records simulated payout in SQLite ledger with strict idempotency.
        Prevents duplicate ACH payouts for the same claim.
        """
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if already disbursed
        cursor.execute("SELECT txn_id, amount, status, created_at FROM simulated_ledger WHERE claim_id = ?;", (claim_id,))
        existing = cursor.fetchone()
        
        if existing:
            conn.close()
            return {
                "success": True,
                "is_duplicate": True,
                "txn_id": existing["txn_id"],
                "amount": existing["amount"],
                "status": existing["status"],
                "disbursed_at": existing["created_at"],
                "message": f"Payment already disbursed under transaction reference {existing['txn_id']}."
            }
            
        txn_id = f"ACH-{uuid.uuid4().hex[:8].upper()}"
        now = datetime.now(timezone.utc).isoformat()
        
        try:
            cursor.execute("""
            INSERT INTO simulated_ledger (txn_id, claim_id, amount, recipient, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?);
            """, (txn_id, claim_id, amount, recipient, "DISBURSED", now))
            conn.commit()
            conn.close()
            
            return {
                "success": True,
                "is_duplicate": False,
                "txn_id": txn_id,
                "amount": amount,
                "status": "DISBURSED",
                "disbursed_at": now,
                "message": f"Simulated ACH payment of ${amount:,.2f} disbursed successfully."
            }
        except Exception as e:
            conn.close()
            return {
                "success": False,
                "is_duplicate": False,
                "error": str(e)
            }
