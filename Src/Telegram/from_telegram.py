import os, asyncio
from dotenv import load_dotenv
from telegram import Bot

load_dotenv()

async def main():
    bot = Bot(os.getenv("BOT_TOKEN"))
    async with bot:
        updates = await bot.get_updates(offset=-1)
        if updates:
            raw = updates[0].message.text
            indices = sorted([int(x) for x in raw.split() if x.isdigit()])
            print(indices)
            await bot.get_updates(offset=updates[0].update_id + 1)

if __name__ == "__main__":
    asyncio.run(main())