import base64
import hashlib
import json
import secrets
import unittest
from unittest.mock import patch

from fastapi import HTTPException

import cbor2
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa

from web.database import transaction
from web.services.bank_client import settle_payment
from web.routers.webauthn import ORIGIN, RP_ID
from tests import login, request
from tests.section2.test_oauth import connect_bank

PREFIX = "/section-2"
PASSKEY = PREFIX + "/webauthn"


def encode(data):
    return base64.urlsafe_b64encode(data).decode().rstrip("=")


def client_data(kind, options):
    return json.dumps({"type": kind, "challenge": options["publicKey"]["challenge"],
                       "origin": ORIGIN, "crossOrigin": False}).encode()


def credential(identifier, **fields):
    key = encode(identifier)
    return {"id": key, "rawId": key, "type": "public-key",
            "response": {name: encode(value) for name, value in fields.items()}}


class PaymentTests(unittest.TestCase):
    def test_passkey_signature_and_payment(self):
        username, token = login()
        connect_bank(token, ["payments:write"])
        status, _, payment = request("POST", PREFIX + "/payments", {"amount_krw": 1000}, token)
        self.assertEqual(status, 201)
        payment_path = PREFIX + "/payments/" + payment["id"]
        self.assertEqual(request("GET", payment_path + "/receipt", token=token)[0], 409)

        status, _, options = request("POST", PASSKEY + "/register/options", {}, token)
        self.assertEqual(status, 200)
        self.assertEqual(options["publicKey"]["pubKeyCredParams"], [{"type": "public-key", "alg": -257}])
        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        public = key.public_key().public_numbers()
        cose = cbor2.dumps({
            1: 3, 3: -257, -1: public.n.to_bytes(256, "big"), -2: public.e.to_bytes(3, "big"),
        })
        rp_hash = hashlib.sha256(RP_ID.encode()).digest()
        identifier = secrets.token_bytes(32)
        auth = rp_hash + bytes([0x45]) + bytes(4) + bytes(16)
        auth += len(identifier).to_bytes(2, "big") + identifier + cose
        attestation = cbor2.dumps({"fmt": "none", "attStmt": {}, "authData": auth})
        body = {
            "challenge_id": options["challenge_id"],
            "credential": credential(identifier, clientDataJSON=client_data("webauthn.create", options),
                                     attestationObject=attestation),
        }
        status, _, data = request("POST", PASSKEY + "/register/verify", body, token)
        self.assertEqual(status, 200, data)

        status, _, options = request("POST", f"{PASSKEY}/approve/{payment['id']}/options", {}, token)
        self.assertEqual(status, 200)
        client = client_data("webauthn.get", options)
        auth = rp_hash + bytes([0x05]) + (1).to_bytes(4, "big")
        signature = key.sign(auth + hashlib.sha256(client).digest(), padding.PKCS1v15(), hashes.SHA256())
        body = {
            "challenge_id": options["challenge_id"],
            "credential": credential(identifier, clientDataJSON=client, authenticatorData=auth,
                                     signature=signature),
        }
        verify_path = PASSKEY + "/approve/verify"
        with patch("web.services.payment.bank_client.settle_payment", side_effect=HTTPException(503)):
            self.assertEqual(request("POST", verify_path, body, token)[0], 503)
        self.assertEqual(request("GET", payment_path, token=token)[2]["status"], "pending")

        settled = {}

        def lose_bank_response(*args):
            settled.update(settle_payment(*args))
            raise HTTPException(503)

        with patch("web.services.payment.bank_client.settle_payment", side_effect=lose_bank_response):
            self.assertEqual(request("POST", verify_path, body, token)[0], 503)
        self.assertEqual(request("GET", payment_path, token=token)[2]["status"], "pending")

        status, _, complete = request("POST", verify_path, body, token)
        self.assertEqual(status, 200, complete)
        self.assertEqual(complete["status"], "completed")
        self.assertTrue(complete["encrypted_receipt"])
        self.assertEqual(request("POST", PASSKEY + "/approve/verify", body, token)[0], 400)
        status, _, receipt = request("GET", payment_path + "/receipt", token=token)
        self.assertEqual(status, 200)
        self.assertEqual(receipt["amount_krw"], 1000)
        self.assertEqual(receipt, settled)
        with transaction() as db:
            retried = settle_payment(db, username, 1000, payment["id"])
        self.assertEqual(retried, receipt)
        _, stranger = login()
        self.assertEqual(request("GET", payment_path, token=stranger)[0], 404)

    def test_rate_limit(self):
        _, token = login()
        connect_bank(token, ["payments:write"])
        for _ in range(3):
            self.assertEqual(request("POST", PREFIX + "/payments", {"amount_krw": 5}, token)[0], 201)
        status, headers, _ = request("POST", PREFIX + "/payments", {"amount_krw": 5}, token)
        self.assertEqual(status, 429)
        self.assertGreater(int(headers["Retry-After"]), 0)
