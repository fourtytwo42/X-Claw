import pathlib
import sys
import unittest
from unittest import mock
import types

RUNTIME_ROOT = pathlib.Path("apps/agent-runtime").resolve()
if str(RUNTIME_ROOT) not in sys.path:
    sys.path.insert(0, str(RUNTIME_ROOT))

from xclaw_agent.liquidity_adapter import (  # noqa: E402
    AmmV2LiquidityAdapter,
    AmmV3LiquidityAdapter,
    HederaHtsLiquidityAdapter,
    HederaSdkUnavailable,
    LiquidityAdapterError,
    UnsupportedLiquidityAdapter,
    build_liquidity_adapter,
    build_liquidity_adapter_for_request,
)
from xclaw_agent import hedera_hts_plugin  # noqa: E402


class LiquidityAdapterTests(unittest.TestCase):
    def test_hts_bridge_command_defaults_to_repo_bridge(self) -> None:
        with mock.patch.dict(hedera_hts_plugin.os.environ, {"XCLAW_HEDERA_HTS_BRIDGE_CMD": ""}, clear=False):
            cmd = hedera_hts_plugin._bridge_command()
        self.assertGreaterEqual(len(cmd), 2)
        self.assertTrue(cmd[1].endswith("xclaw_agent/bridges/hedera_hts_bridge.py"))

    def test_hts_bridge_command_env_override_honored(self) -> None:
        with mock.patch.dict(
            hedera_hts_plugin.os.environ,
            {"XCLAW_HEDERA_HTS_BRIDGE_CMD": "python /tmp/custom_bridge.py --flag"},
            clear=False,
        ):
            cmd = hedera_hts_plugin._bridge_command()
        self.assertEqual(cmd, ["python", "/tmp/custom_bridge.py", "--flag"])

    def test_build_selects_v2_default(self) -> None:
        adapter = build_liquidity_adapter("base_sepolia", "uniswap_v2", "amm_v2")
        self.assertIsInstance(adapter, AmmV2LiquidityAdapter)

    def test_build_selects_v3(self) -> None:
        adapter = build_liquidity_adapter("base_sepolia", "uniswap_v3", "amm_v3", position_type="v3")
        self.assertIsInstance(adapter, AmmV3LiquidityAdapter)

    def test_build_selects_hedera_hts(self) -> None:
        adapter = build_liquidity_adapter("hedera_testnet", "hedera_hts", "hedera_hts")
        self.assertIsInstance(adapter, HederaHtsLiquidityAdapter)

    def test_hedera_adapter_fails_closed_without_sdk(self) -> None:
        adapter = HederaHtsLiquidityAdapter(chain="hedera_testnet", dex="hedera_hts", protocol_family="hedera_hts", position_type="v2")
        with mock.patch("builtins.__import__", side_effect=ModuleNotFoundError("no module named hedera")):
            with self.assertRaises(HederaSdkUnavailable):
                adapter.quote_add({"amountA": "1", "amountB": "1", "slippageBps": 100})

    def test_hedera_add_uses_plugin_bridge(self) -> None:
        adapter = HederaHtsLiquidityAdapter(chain="hedera_testnet", dex="hedera_hts", protocol_family="hedera_hts", position_type="v2")
        plugin = types.SimpleNamespace(
            execute_liquidity=mock.Mock(return_value={"txHash": "0xabc", "positionId": "pos_1", "details": {"network": "hedera"}})
        )
        with mock.patch.object(adapter, "ensure_sdk"), mock.patch("importlib.import_module", return_value=plugin):
            result = adapter.add({"amountA": "1", "amountB": "1", "slippageBps": 100})
        self.assertEqual(result.get("txHash"), "0xabc")
        self.assertEqual(result.get("positionId"), "pos_1")
        self.assertEqual(result.get("details"), {"network": "hedera"})
        self.assertTrue(plugin.execute_liquidity.called)

    def test_hedera_add_plugin_missing_tx_hash_fails(self) -> None:
        adapter = HederaHtsLiquidityAdapter(chain="hedera_testnet", dex="hedera_hts", protocol_family="hedera_hts", position_type="v2")
        plugin = types.SimpleNamespace(execute_liquidity=mock.Mock(return_value={"ok": True}))
        with mock.patch.object(adapter, "ensure_sdk"), mock.patch("importlib.import_module", return_value=plugin):
            with self.assertRaises(LiquidityAdapterError):
                adapter.add({"amountA": "1", "amountB": "1", "slippageBps": 100})

    def test_hedera_plugin_bridge_missing_module_fails_closed(self) -> None:
        adapter = HederaHtsLiquidityAdapter(chain="hedera_testnet", dex="hedera_hts", protocol_family="hedera_hts", position_type="v2")
        with mock.patch.object(adapter, "ensure_sdk"), mock.patch("importlib.import_module", side_effect=ModuleNotFoundError("no plugin")):
            with self.assertRaises(HederaSdkUnavailable):
                adapter.add({"amountA": "1", "amountB": "1", "slippageBps": 100})

    def test_resolve_adapter_from_chain_config(self) -> None:
        adapter = build_liquidity_adapter_for_request("base_sepolia", "aerodrome", "v2")
        self.assertIsInstance(adapter, AmmV2LiquidityAdapter)
        self.assertEqual(adapter.protocol_family, "amm_v2")

    def test_resolve_v3_without_explicit_dex(self) -> None:
        adapter = build_liquidity_adapter_for_request("base_sepolia", "", "v3")
        self.assertIsInstance(adapter, AmmV3LiquidityAdapter)

    def test_resolve_rejects_v3_on_v2_only_adapter(self) -> None:
        with self.assertRaises(UnsupportedLiquidityAdapter):
            build_liquidity_adapter_for_request("base_sepolia", "aerodrome", "v3")

    def test_resolve_rejects_disabled_protocol(self) -> None:
        with self.assertRaises(UnsupportedLiquidityAdapter):
            build_liquidity_adapter_for_request("kite_ai_testnet", "tesseract_univ3", "v3")

    def test_resolve_hedera_evm_protocols(self) -> None:
        saucer = build_liquidity_adapter_for_request("hedera_testnet", "saucerswap", "v2")
        pangolin = build_liquidity_adapter_for_request("hedera_testnet", "pangolin", "v2")
        self.assertEqual(saucer.protocol_family, "amm_v2")
        self.assertEqual(pangolin.protocol_family, "amm_v2")

    def test_quote_add_rejects_invalid_amount(self) -> None:
        adapter = AmmV2LiquidityAdapter(chain="base_sepolia", dex="aerodrome", protocol_family="amm_v2", position_type="v2")
        with self.assertRaises(LiquidityAdapterError):
            adapter.quote_add({"amountA": "0", "amountB": "1", "slippageBps": 100})


if __name__ == "__main__":
    unittest.main()
