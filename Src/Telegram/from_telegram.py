import os, asyncio
from dotenv import load_dotenv
from telegram import Bot
from telegram.error import TimedOut, NetworkError
from telegram.request import HTTPXRequest

load_dotenv()

class TelegramFetcher:
    def __init__(self):
        t_request = HTTPXRequest(connect_timeout=30, read_timeout=30)
        self.bot = Bot(token=os.getenv("BOT_TOKEN"), request=t_request)

    async def get_data(self):
        try:
            async with self.bot:
                updates = await self.bot.get_updates(limit=1, allowed_updates=["message"])
                
                if not updates or not updates[0].message or not updates[0].message.text:
                    return {}

                last_update = updates[0]
                lines = [line.strip() for line in last_update.message.text.split('\n') if line.strip()]
                
                result = {}
                for i in range(0, len(lines), 2):
                    if i + 1 < len(lines):
                        link = lines[i]
                        name = lines[i+1]
                        result[f"file{(i//2) + 1}"] = [name, link]
                
                if result:
                    await self.bot.get_updates(offset=last_update.update_id + 1)
                    return result
                
                return {}
        except (TimedOut, NetworkError):
            return {}

if __name__ == "__main__":
    fetcher = TelegramFetcher()
    data = asyncio.run(fetcher.get_data())
    print(data)