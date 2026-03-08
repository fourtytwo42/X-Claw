from __future__ import annotations

import pathlib
import sys
import unittest
from unittest import mock

RUNTIME_ROOT = pathlib.Path("apps/agent-runtime").resolve()
if str(RUNTIME_ROOT) not in sys.path:
    sys.path.insert(0, str(RUNTIME_ROOT))

from xclaw_agent import cli
from xclaw_agent import chains


class ChainAliasTests(unittest.TestCase):
    def test_normalize_chain_key_maps_solana_mainnet_alias(self) -> None:
        self.assertEqual(chains.normalize_chain_key("solana_mainnet"), "solana_mainnet_beta")
        self.assertEqual(chains.normalize_chain_key("solana_mainnet_beta"), "solana_mainnet_beta")

    def test_cli_main_accepts_solana_mainnet_alias(self) -> None:
        observed: dict[str, str] = {}

        def _fake_wallet_address(args):
            observed["chain"] = str(args.chain)
            return 0

        with mock.patch.object(cli, "cmd_wallet_address", side_effect=_fake_wallet_address):
            code = cli.main(["wallet", "address", "--chain", "solana_mainnet", "--json"])

        self.assertEqual(code, 0)
        self.assertEqual(observed.get("chain"), "solana_mainnet_beta")


if __name__ == "__main__":
    unittest.main()
