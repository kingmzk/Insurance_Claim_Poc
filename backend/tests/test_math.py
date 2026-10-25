import pytest

def calculate_payout(approved_estimate: float, deductible: float, depreciation: float) -> float:
    return max(0.0, round(approved_estimate - deductible - depreciation, 2))

def test_settlement_standard_payout():
    # Routine claim: 2950 - 500 - 210 = 2240.00
    payout = calculate_payout(2950.0, 500.0, 210.0)
    assert payout == 2240.00

def test_settlement_high_deductible_zero_payout():
    # Deductions exceed estimate: 1000 - 1500 - 200 -> max(0, -700) = 0.0
    payout = calculate_payout(1000.0, 1500.0, 200.0)
    assert payout == 0.0

def test_settlement_rounding():
    payout = calculate_payout(100.555, 10.222, 5.111)
    assert payout == 85.22
