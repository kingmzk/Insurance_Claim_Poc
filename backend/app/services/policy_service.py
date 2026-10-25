from typing import Dict, Any, List
from ..db.database import search_policy_clauses

# Authoritative Policy Administration System (PAS) Mock Registry
MOCK_POLICIES = {
    "POL-AUTO-99201": {
        "policy_no": "POL-AUTO-99201",
        "policyholder": "John Doe",
        "status": "ACTIVE",
        "effective_date": "2026-01-01",
        "expiration_date": "2027-01-01",
        "coverage_type": "Comprehensive & Collision",
        "standard_deductible": 500.0,
        "single_incident_limit": 50000.0,
        "vehicle_vin": "1HGCR2F83HA001234",
        "insured_vehicle": "2023 Honda Accord"
    },
    "POL-AUTO-88104": {
        "policy_no": "POL-AUTO-88104",
        "policyholder": "Marcus Vance",
        "status": "ACTIVE",
        "effective_date": "2026-01-01",
        "expiration_date": "2027-01-01",
        "coverage_type": "Luxury Comprehensive",
        "standard_deductible": 1000.0,
        "single_incident_limit": 100000.0,
        "vehicle_vin": "WAUZZZF28HA009876",
        "insured_vehicle": "2024 Audi RS6 Avant"
    },
    "POL-AUTO-77002": {
        "policy_no": "POL-AUTO-77002",
        "policyholder": "Sarah Jenkins",
        "status": "LAPSED",
        "effective_date": "2025-01-01",
        "expiration_date": "2025-12-31",
        "coverage_type": "Standard Collision",
        "standard_deductible": 500.0,
        "single_incident_limit": 30000.0,
        "vehicle_vin": "JTDKN3DU5E1005544",
        "insured_vehicle": "2022 Toyota Prius"
    }
}

class PolicyService:
    @staticmethod
    def get_policy_status(policy_no: str) -> Dict[str, Any]:
        """Queries authoritative Policy Administration System (PAS) for status and limits."""
        policy = MOCK_POLICIES.get(policy_no)
        if not policy:
            return {
                "found": False,
                "status": "NOT_FOUND",
                "message": f"Policy {policy_no} not registered in policy system."
            }
        return {
            "found": True,
            **policy
        }

    @staticmethod
    def retrieve_clauses(policy_no: str, query: str) -> List[Dict[str, Any]]:
        """Retrieves exact policy clauses using SQLite FTS5."""
        return search_policy_clauses(query=query, policy_no=policy_no, limit=4)
