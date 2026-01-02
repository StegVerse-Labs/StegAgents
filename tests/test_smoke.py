def test_repo_imports():
    import src.agent_runner  # verifies import graph


def test_receipt_verify_local():
    from src.receipt_verify import verify_receipt
    receipt = {"issuer": "local", "verified": True}
    assert isinstance(verify_receipt(receipt), dict)
