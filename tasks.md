# Slice 234 Tasks: Telegram Messaging + Delivery Cleanup Services (2026-03-08)

Issue mapping: `#87`

- [x] Extract Telegram transfer/policy/liquidity prompt send helpers into `runtime/services/telegram_delivery.py`.
- [x] Extract Telegram decision/terminal/cleanup/bot-token helpers into `runtime/services/telegram_delivery.py`.
- [x] Extract active-chat owner-link delivery helper into `runtime/services/owner_link_delivery.py`.
- [x] Keep `cli.py` wrappers thin and preserve current patch/test seams.
- [x] Add direct runtime service coverage for the moved seams.
- [x] Run full sequential validations + capture evidence in `acceptance.md`.
