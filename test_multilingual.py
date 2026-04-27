"""Test multilingual chat flow without langdetect — Azure OpenAI handles detection natively."""

import asyncio
from cafebot import CafeBotEngine

engine = CafeBotEngine()

TEST_CASES = [
    ("user_id_1", "Indonesian", "Halo! Saya merasa sangat lelah hari ini"),
    ("user_id_2", "Chinese", "你好！我今天很累"),
    ("user_id_3", "Japanese", "こんにちは！今日はとても疲れています"),
    ("user_id_4", "Korean", "안녕하세요! 오늘 너무 피곤해요"),
    ("user_id_5", "Spanish", "¡Hola! Me siento muy cansado hoy"),
    ("user_id_6", "English", "Hey! I'm feeling super tired today"),
]


async def run_tests() -> None:
    print("=" * 60)
    print("  Multilingual Test — Azure OpenAI Native Detection")
    print(f"  LLM Available: {engine._llm.available}")
    print("=" * 60)

    if not engine._llm.available:
        print("\n  Azure OpenAI not configured — skipping LLM tests.")
        print("  Set AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_KEY, and")
        print("  AZURE_OPENAI_DEPLOYMENT_NAME in .env to test.")
        return

    for user_id, lang, message in TEST_CASES:
        print(f"\n  [{lang}] User: {message}")
        reply = await engine.chat(user_id, message)
        print(f"  Bot: {reply[:300]}{'...' if len(reply) > 300 else ''}")
        print(f"  {'✅' if reply else '❌'} Response received")

    print("\n" + "=" * 60)
    print("  Test complete!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(run_tests())
