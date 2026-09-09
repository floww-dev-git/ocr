from document_extraction.adapters.qr_decode import parse_qr_payload


class TestParseQrPayload:
    def test_it_parses_our_payload_into_catalog_field_keys(self):
        payload = (
            "AADHAAR|name=Rithika Sharma|uid=234567890124|dob=1990-06-15|gender=Female"
        )
        assert parse_qr_payload(payload) == {
            "name": "Rithika Sharma",
            "aadhaarNo": "234567890124",
            "dob": "1990-06-15",
            "gender": "Female",
        }

    def test_a_payload_that_is_not_ours_is_ignored(self):
        # A production Aadhaar secure-QR is not our plain-text format; we do not
        # pretend to read it.
        assert parse_qr_payload("<?xml version='1.0'?><PrintLetterBarcodeData/>") is None
        assert parse_qr_payload("https://example.com") is None
        assert parse_qr_payload("") is None

    def test_missing_parts_are_simply_absent(self):
        payload = "AADHAAR|name=Rithika Sharma|uid=234567890124"
        parsed = parse_qr_payload(payload)
        assert parsed == {"name": "Rithika Sharma", "aadhaarNo": "234567890124"}

    def test_an_empty_bodied_payload_is_none(self):
        assert parse_qr_payload("AADHAAR") is None
