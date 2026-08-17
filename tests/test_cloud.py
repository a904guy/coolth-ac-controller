import unittest

from coolth import config
from coolth.cloud import ApiError, CloudError, NetHomePlusCloud, SmartHomeCloud
from coolth.const import DEFAULT_CLOUD_REGION

# Credentials for live cloud tests are read from the coolth config object (a
# config file, see coolth.config). Live tests are skipped unless an account and
# password are configured, so no credentials are ever hard coded here.
config.load_config_file()
_ACCOUNT = config.get("account")
_PASSWORD = config.get("password")
_REGION = config.get("region") or DEFAULT_CLOUD_REGION
_HAVE_CREDS = bool(_ACCOUNT and _PASSWORD)
_SKIP_REASON = "No cloud credentials configured (set account/password in the coolth config)."


class TestCloudErrors(unittest.IsolatedAsyncioTestCase):
    """Error handling that needs no real credentials."""
    # pylint: disable=protected-access

    def test_invalid_region(self) -> None:
        """An unknown region with no explicit credentials raises."""
        with self.assertRaises(ValueError):
            NetHomePlusCloud("NOT_A_REGION")

    def test_partial_credentials(self) -> None:
        """Supplying only an account or only a password raises."""
        with self.assertRaises(ValueError):
            NetHomePlusCloud(_REGION, account="some_account", password=None)
        with self.assertRaises(ValueError):
            NetHomePlusCloud(_REGION, account=None, password="some_password")

    async def test_connect_exception(self) -> None:
        """A bad server URL raises a CloudError, before credentials matter."""
        client = NetHomePlusCloud(
            _REGION, account="dummy@example.com", password="dummy")
        client._base_url = "https://fake_server.invalid."
        with self.assertRaises(CloudError):
            await client.login()


@unittest.skipUnless(_HAVE_CREDS, _SKIP_REASON)
class TestNetHomePlusCloudLive(unittest.IsolatedAsyncioTestCase):
    """Live tests against the NetHome Plus cloud using configured credentials."""
    # pylint: disable=protected-access

    async def _login(self) -> NetHomePlusCloud:
        client = NetHomePlusCloud(
            _REGION, account=_ACCOUNT, password=_PASSWORD)
        await client.login()
        return client

    async def test_login(self) -> None:
        client = await self._login()
        self.assertIsNotNone(client._session)
        self.assertIsNotNone(client._session_id)

    async def test_login_bad_password(self) -> None:
        """A wrong password for a real account raises an ApiError."""
        client = NetHomePlusCloud(
            _REGION, account=_ACCOUNT, password="definitely_not_the_password")
        with self.assertRaises(ApiError):
            await client.login()


@unittest.skipUnless(_HAVE_CREDS, _SKIP_REASON)
class TestSmartHomeCloudLive(unittest.IsolatedAsyncioTestCase):
    """Live SmartHome cloud tests. Requires the configured account to be valid
    for the SmartHome/MSmartHome app; skipped otherwise."""
    # pylint: disable=protected-access

    async def test_connect_exception(self) -> None:
        client = SmartHomeCloud(
            _REGION, account="dummy@example.com", password="dummy")
        client._base_url = "https://fake_server.invalid."
        with self.assertRaises(CloudError):
            await client.login()


if __name__ == "__main__":
    unittest.main()
