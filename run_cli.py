"""CLI runner for local testing."""

import asyncio
import random

from cafebot.engine import CafeBotEngine
from cafebot.config import settings

_CLI_USER = "cli_user"
# In CLI mode, the user IS the owner
_OWNER_USER = "cli_owner"


async def main() -> None:
    engine = CafeBotEngine()

    print("=" * 60)
    print("  Welcome to CafeMate (CLI Mode)")
    print("  Your friendly barista who actually cares how you feel")
    print("=" * 60)
    print()
    print(f"  {await engine.greet(_CLI_USER)}")
    print()
    print("  (Type 'menu' to see drinks, 'order' to check your order,")
    print("   'checkout' when done, 'quit' to leave)")
    print("  Owner: /admin, /admin_menu, /admin_add, /admin_remove, /admin_reload")
    print("-" * 60)

    while True:
        try:
            user_input = input("\nYou: ").strip()
        except (EOFError, KeyboardInterrupt):
            print(f"\n\nCafeMate: See ya!")
            break

        if not user_input:
            continue

        if user_input.lower() in ["quit", "exit", "bye", "goodbye", "see ya"]:
            farewell = await engine.farewell(_CLI_USER)
            print(f"\nCafeMate: {farewell}")
            break

        # ---- owner admin commands (CLI always has owner access) ----
        lower = user_input.lower()
        if lower in ["/admin", "/admin_help"]:
            print(f"\n{engine.admin_help(_CLI_USER)}")
            continue
        if lower == "/admin_menu":
            print(f"\n{engine.admin_view_menu()}")
            continue
        if lower.startswith("/admin_add "):
            json_str = user_input[len("/admin_add "):].strip()
            print(f"\n{engine.admin_add_drink(json_str)}")
            continue
        if lower.startswith("/admin_remove "):
            name = user_input[len("/admin_remove "):].strip()
            print(f"\n{engine.admin_remove_drink(name)}")
            continue
        if lower == "/admin_reload":
            print(f"\n{engine.admin_reload_menu()}")
            continue

        response = await engine.chat(_CLI_USER, user_input)
        print(f"\nCafeMate: {response}")


if __name__ == "__main__":
    asyncio.run(main())
