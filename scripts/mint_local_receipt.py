#!/usr/bin/env python3
import json
import os
import datetime

agent = os.environ.get("SV_AGENT", "unknown")

receipt = {
    "issuer": "local",
    "agent": agent,
    "issued_at": datetime.datetime.utcnow().isoformat() + "Z",
    "verified": True,
    "verifier": "local",
}

print(json.dumps(receipt))
