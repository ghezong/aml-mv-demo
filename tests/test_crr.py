from aml_mv_demo.crr import calculate_activation_crr
from aml_mv_demo.data_generator import generate_synthetic_data


def test_activation_crr_has_reason_codes_and_tiers():
    customers, _, _, _ = generate_synthetic_data(seed=7)
    result = calculate_activation_crr(customers)

    assert {"customer_id", "activation_crr_score", "activation_crr_tier", "activation_reason_codes"}.issubset(result.columns)
    assert result["activation_crr_score"].between(0, 100).all()
    assert set(result["activation_crr_tier"]).issubset({"low", "medium", "high"})
