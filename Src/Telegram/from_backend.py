import os, asyncio
from dotenv import load_dotenv
from telegram import Bot

load_dotenv()
ITEMS = ["Hi 1GB", "Ball 58GB", "Cat KS", "Dog", "Elephetkjdhkdh 10GB", "Fruit", "Graph", "Hype", "Ice"]

async def main():
    bot = Bot(os.getenv("BOT_TOKEN"))
    text = "Reply with numbers (e.g., 5 6 8):\n" + "\n".join(f"{i}. {x}" for i, x in enumerate(ITEMS))
    async with bot:
        await bot.send_message(os.getenv("USER_ID"), text)

if __name__ == "__main__":
    asyncio.run(main())