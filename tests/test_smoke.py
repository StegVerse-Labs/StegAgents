def test_repo_imports():
    import src.agent_runner


def test_local_receipt_verifier():
    from src.receipt_verify import verify_receipt
    receipt = {"issuer": "local", "verified": True}
    out = verify_receipt(receipt)
    assert isinstance(out, dict)
