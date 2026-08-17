import hashlib
import unittest

from Crypto.Cipher import AES
from Crypto.Util import Padding

from coolth import config
from coolth.cloud_lan import CloudLAN, _extract_aa, _timestamp, build_5a5a_packet

# Live integration credentials come from the coolth config object; the live test
# is skipped unless account, password and an appliance host are configured.
config.load_config_file()
_ACCOUNT = config.get("account")
_PASSWORD = config.get("password")
_HOST = config.get("host")
_HAVE_LIVE = bool(_ACCOUNT and _PASSWORD and _HOST and str(_HOST).isdigit())
_SKIP_REASON = "No cloud credentials/host configured for a live cloud test."

# A short, well-formed AC query frame for structural tests (not sent anywhere).
_SAMPLE_FRAME = bytes.fromhex(
    "aa21ac00000000000303418100ff03ff00020000000000000000000000000304560b")


class TestPacket(unittest.TestCase):

    def test_timestamp_shape(self) -> None:
        ts = _timestamp()
        self.assertEqual(len(ts), 8)
        # month is stored 0-indexed, so it is always <= 11
        self.assertLessEqual(ts[5], 11)
        # hour is 12-hour, so always <= 11
        self.assertLessEqual(ts[3], 11)

    def test_packet_structure(self) -> None:
        appliance_id = 151732606158606
        packet = build_5a5a_packet(_SAMPLE_FRAME, appliance_id, seq=1234)

        # Magic and version
        self.assertEqual(packet[0:2], b"\x5A\x5A")
        self.assertEqual(packet[2], 0x01)
        # Length field matches actual length and equals frame + 56
        self.assertEqual(int.from_bytes(packet[4:6], "little"), len(packet))
        self.assertEqual(len(packet), len(_SAMPLE_FRAME) + 56)
        # Magic 0x0020
        self.assertEqual(int.from_bytes(packet[6:8], "little"), 32)
        # Sequence
        self.assertEqual(int.from_bytes(packet[8:12], "little"), 1234)
        # Appliance id as 6 byte little-endian device tag
        self.assertEqual(packet[20:26], appliance_id.to_bytes(6, "little"))
        # Frame is placed plaintext at offset 40
        self.assertEqual(packet[40:40 + len(_SAMPLE_FRAME)], _SAMPLE_FRAME)

    def test_extract_aa_roundtrip(self) -> None:
        packet = build_5a5a_packet(_SAMPLE_FRAME, 151732606158606, seq=1)
        self.assertEqual(_extract_aa(packet), _SAMPLE_FRAME)

    def test_extract_aa_none_when_absent(self) -> None:
        self.assertIsNone(_extract_aa(b"\x00" * 40))


class TestCrypto(unittest.TestCase):

    def _client(self) -> CloudLAN:
        # No network is used; credentials here are placeholders for construction.
        return CloudLAN(151732606158606, "unused@example.com", "unused")

    def test_text_roundtrip(self) -> None:
        client = self._client()
        data = bytes(range(256))
        text = client._to_text(data)
        self.assertEqual(client._from_text(text.decode()), data)

    def test_sign_matches_reference(self) -> None:
        client = self._client()
        body = {"b": "2", "a": "1"}
        expected = hashlib.sha256(
            ("/path" + "a=1&b=2" + client._app_key).encode()).hexdigest()
        self.assertEqual(client._sign("/path", body), expected)

    def test_password_hash_matches_reference(self) -> None:
        client = self._client()
        login_id = "LOGINID"
        pw = "hunter2"
        m1 = hashlib.sha256(pw.encode("ASCII")).hexdigest()
        expected = hashlib.sha256(
            (login_id + m1 + client._app_key).encode("ASCII")).hexdigest()
        # Reach the inner helper via a temporary password.
        client._password = pw
        self.assertEqual(client._password_hash(login_id), expected)

    def test_derive_key(self) -> None:
        client = self._client()
        # Construct a fake access token that decrypts to a known 16-byte key.
        known_key = b"0123456789abcdef"
        k = hashlib.md5(client._app_key.encode()).hexdigest()[:16].encode()
        token = AES.new(k, AES.MODE_ECB).encrypt(Padding.pad(known_key, 16)).hex()
        self.assertEqual(client._derive_key(token), known_key)

    def test_order_roundtrip(self) -> None:
        client = self._client()
        client._key = b"0123456789abcdef"
        client._iv = b"fedcba9876543210"
        packet = build_5a5a_packet(_SAMPLE_FRAME, 151732606158606, seq=7)
        order = client._encrypt_order(packet)
        self.assertEqual(client._decrypt_reply(order), packet)

    def test_iv_recovery_math(self) -> None:
        """The IV recovery formula returns the true IV from the server echo."""
        key = b"0123456789abcdef"
        true_iv = b"fedcba9876543210"
        zero = b"\x00" * 16

        # Plaintext (as the wire text) and our ciphertext using a zero IV.
        text = CloudLAN._to_text(build_5a5a_packet(_SAMPLE_FRAME, 1, seq=1))
        our_ct = AES.new(key, AES.MODE_CBC, iv=zero).encrypt(Padding.pad(text, 16))

        # The server decrypts our ciphertext with the true IV. With a wrong IV
        # only block 1 differs; that difference is what it echoes back.
        echoed = AES.new(key, AES.MODE_CBC, iv=true_iv).decrypt(our_ct)

        recovered = bytes(text[i] ^ zero[i] ^ echoed[i] for i in range(16))
        self.assertEqual(recovered, true_iv)


@unittest.skipUnless(_HAVE_LIVE, _SKIP_REASON)
class TestCloudLANLive(unittest.IsolatedAsyncioTestCase):
    """Live round trip using configured credentials. Reads state only; makes no
    changes to the device."""

    async def test_login_and_refresh(self) -> None:
        from coolth.device import AirConditioner as AC

        cloud = CloudLAN(int(_HOST), _ACCOUNT, _PASSWORD)
        await cloud.login()

        device = AC(ip="cloud", port=0, device_id=int(_HOST))
        device._lan = cloud
        await device.refresh()

        self.assertTrue(device.online)
        self.assertIsNotNone(device.target_temperature)


if __name__ == "__main__":
    unittest.main()
