from typing import List, Dict, Any
from datetime import datetime

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
                "requires_siu": False
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
                    # Support formats like YYYY-MM-DD or ISO
                    exif_dt = datetime.fromisoformat(exif_ts[:10])
                    loss_dt = datetime.fromisoformat(reported_loss_date[:10])
                    
                    # If photo was taken more than 1 day before incident date
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
            score = 12  # Normal baseline risk score

        return {
            "fraud_score": min(score, 100),
            "flags": flags,
            "duplicate_matches": duplicate_matches,
            "exif_discrepancies": exif_discrepancies,
            "requires_siu": score >= 75
        }
