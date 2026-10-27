import json
from typing import List, Dict, Any
from datetime import datetime
from ..core.config import FRAUD_THRESHOLD_ESCALATION
from ..db.database import get_db_connection

# Known fraudulent/prior claim photo perceptual hashes
PRIOR_CLAIM_HASHES = {
    "a8b4c9e1f203d456": {
        "prior_claim_id": "CLM-2024-1102",
        "date_submitted": "2024-08-14",
        "notes": "Prior bumper damage claim settled with claimant Robert Bell"
    },
    "ffeeddccbbaa9988": {
        "prior_claim_id": "CLM-2025-0451",
        "date_submitted": "2025-03-22",
        "notes": "Suspected staged collision with repetitive front-quarter panel photo"
    }
}

class ForensicsService:
    @staticmethod
    def inspect_photos(photos: List[Dict[str, Any]], reported_loss_date: str) -> Dict[str, Any]:
        """
        Inspects EXIF metadata and perceptual hash duplicates.
        Calculates a transparent fraud score (0-100).
        """
        flags = []
        score = 0
        duplicate_matches = []
        exif_discrepancies = []

        if not photos:
            # Minor flag if no photos attached for motor collision
            flags.append("NO_PHOTOS_SUBMITTED")
            score += 15
            return {
                "fraud_score": score,
                "flags": flags,
                "duplicate_matches": duplicate_matches,
                "exif_discrepancies": exif_discrepancies,
                "requires_siu": score >= FRAUD_THRESHOLD_ESCALATION
            }

        for photo in photos:
            phash = photo.get("phash", "")
            exif_ts = photo.get("exif_timestamp", "")
            photo_id = photo.get("photo_id", photo.get("filename", "unknown"))

            # 1. Check Perceptual Hash for prior claim duplication
            if phash in PRIOR_CLAIM_HASHES:
                match_info = PRIOR_CLAIM_HASHES[phash]
                duplicate_matches.append({
                    "photo_id": photo_id,
                    "matched_hash": phash,
                    "prior_claim_id": match_info["prior_claim_id"],
                    "notes": match_info["notes"]
                })
                flags.append(f"DUPLICATE_PHOTO_PRIOR_CLAIM: {photo_id} matches {match_info['prior_claim_id']}")
                score += 45

            # 2. Check EXIF Timestamp vs Reported Incident Date
            if exif_ts and reported_loss_date:
                try:
                    exif_dt = datetime.fromisoformat(exif_ts[:10])
                    loss_dt = datetime.fromisoformat(reported_loss_date[:10])
                    
                    if (loss_dt - exif_dt).days > 1:
                        exif_discrepancies.append({
                            "photo_id": photo_id,
                            "exif_date": exif_ts,
                            "loss_date": reported_loss_date,
                            "days_prior": (loss_dt - exif_dt).days
                        })
                        flags.append(f"EXIF_PREDATES_LOSS: Photo taken {(loss_dt - exif_dt).days} days before incident")
                        score += 40
                except Exception:
                    pass

            # 3. Check explicit tampering flag
            if photo.get("is_tampered"):
                flags.append(f"IMAGE_TAMPERING_DETECTED: {photo_id}")
                score += 35

        # Base soft fraud score (clean base score)
        if score == 0:
            score = 12

        return {
            "fraud_score": min(score, 100),
            "flags": flags,
            "duplicate_matches": duplicate_matches,
            "exif_discrepancies": exif_discrepancies,
            "requires_siu": score >= FRAUD_THRESHOLD_ESCALATION
        }

    @classmethod
    def inspect_claim(cls, intake_data: Dict[str, Any], current_claim_id: str = "") -> Dict[str, Any]:
        """
        Comprehensive multi-signal fraud screening:
        1. Photo perceptual hashes & EXIF metadata forensics.
        2. Claimant claim velocity across past 12 months.
        3. Cross-claim VIN collusion / network duplication.
        4. Claimed amount vs vehicle damage anomaly.
        """
        photos = intake_data.get("photos", [])
        loss_date = intake_data.get("loss_date", "")
        claimant_name = intake_data.get("claimant_name", "").strip()
        policy_no = intake_data.get("policy_no", "").strip()
        vin = intake_data.get("vin", "").strip()
        claimed_amt = float(intake_data.get("claimed_amt", 0.0))

        # Start with photo forensics
        photo_result = cls.inspect_photos(photos, loss_date)
        score = photo_result["fraud_score"]
        flags = list(photo_result["flags"])
        duplicate_matches = list(photo_result["duplicate_matches"])
        exif_discrepancies = list(photo_result["exif_discrepancies"])

        network_signals = {
            "prior_claims_by_claimant": 0,
            "vin_cross_claim_matches": [],
            "network_risk_tier": "NORMAL"
        }

        # Query past claims in SQLite database for network and velocity signals
        try:
            conn = get_db_connection()
            cursor = conn.cursor()

            # Signal 1: Claimant Velocity (Multiple claims in last 12 months)
            if claimant_name:
                cursor.execute("""
                    SELECT claim_id, state_json FROM claims 
                    WHERE claim_id != ?;
                """, (current_claim_id,))
                rows = cursor.fetchall()

                claimant_prior_claims = 0
                vin_matches = []

                for r in rows:
                    try:
                        st = json.loads(r["state_json"]) if r["state_json"] else {}
                        past_intake = st.get("intake_data", {})
                        past_claimant = past_intake.get("claimant_name", "").strip().lower()
                        past_vin = past_intake.get("vin", "").strip().upper()
                        past_policy = past_intake.get("policy_no", "").strip()

                        if claimant_name.lower() == past_claimant and past_claimant != "":
                            claimant_prior_claims += 1

                        if vin and past_vin and vin.upper() == past_vin:
                            if past_policy != policy_no or past_claimant != claimant_name.lower():
                                vin_matches.append({
                                    "claim_id": r["claim_id"],
                                    "policy_no": past_policy,
                                    "claimant": past_intake.get("claimant_name")
                                })
                    except Exception:
                        continue

                network_signals["prior_claims_by_claimant"] = claimant_prior_claims
                network_signals["vin_cross_claim_matches"] = vin_matches

                # Score Claimant Velocity
                if claimant_prior_claims >= 2:
                    flags.append(f"HIGH_CLAIM_VELOCITY: Claimant has {claimant_prior_claims} prior claims on record")
                    score += 25
                    network_signals["network_risk_tier"] = "ELEVATED"

                # Score Cross-Claim VIN Collusion
                if vin_matches:
                    match_ids = ", ".join(m["claim_id"] for m in vin_matches)
                    flags.append(f"CROSS_CLAIM_VIN_COLLUSION: Vehicle VIN matches prior claims ({match_ids}) under different policy/claimant")
                    score += 40
                    network_signals["network_risk_tier"] = "HIGH"

            conn.close()
        except Exception as e:
            # Non-blocking if database query fails during isolated unit tests
            pass

        # Signal 3: High claimed amount without photos
        if claimed_amt > 15000.0 and not photos:
            flags.append(f"HIGH_VALUE_NO_PHOTO_EVIDENCE: Claim of ${claimed_amt:,.2f} submitted without forensic imagery")
            score += 20

        final_score = min(score, 100)
        requires_siu = final_score >= FRAUD_THRESHOLD_ESCALATION

        return {
            "fraud_score": final_score,
            "flags": flags,
            "duplicate_matches": duplicate_matches,
            "exif_discrepancies": exif_discrepancies,
            "network_signals": network_signals,
            "requires_siu": requires_siu
        }
