import pathlib
import sys
import unittest

RUNTIME_ROOT = pathlib.Path("apps/agent-runtime").resolve()
if str(RUNTIME_ROOT) not in sys.path:
    sys.path.insert(0, str(RUNTIME_ROOT))

from xclaw_agent.dex_adapter import KiteTesseractAdapter, UniswapV2RouterAdapter, build_dex_adapter  # noqa: E402


class DexAdapterTests(unittest.TestCase):
    def test_build_uses_kite_adapter_for_kite_chain(self) -> None:
        adapter = build_dex_adapter(
            chain="kite_ai_testnet",
            cast_bin="cast",
            rpc_url="https://rpc-testnet.gokite.ai/",
            router_address="0x402f35e11cC6E89E80EFF4205956716aCd94be04",
        )
        self.assertIsInstance(adapter, KiteTesseractAdapter)

    def test_build_uses_uniswap_adapter_for_non_kite_chain(self) -> None:
        adapter = build_dex_adapter(
            chain="base_sepolia",
            cast_bin="cast",
            rpc_url="https://sepolia.base.org",
            router_address="0x6dA4720De207105e4Ce1fDD48Dc845798AE2153F",
        )
        self.assertIsInstance(adapter, UniswapV2RouterAdapter)


if __name__ == "__main__":
    unittest.main()
