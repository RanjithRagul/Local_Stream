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
                updates = await self.bot.get_updates(allowed_updates=["message"])
                
                if not updates:
                    return {}

                all_lines = []
                for update in updates:
                    if update.message and update.message.text:
                        text_lines = [line.strip() for line in update.message.text.split('\n') if line.strip()]
                        all_lines.extend(text_lines)

                result = {}
                for i in range(0, len(all_lines), 2):
                    if i + 1 < len(all_lines):
                        link = all_lines[i]
                        name = all_lines[i+1]
                        result[f"file{len(result) + 1}"] = [name, link]

                if result:
                    await self.bot.get_updates(offset=updates[-1].update_id + 1)
                    return result
                return {}
        except (TimedOut, NetworkError):
            return {}

# if __name__ == "__main__":
#     instance = TelegramFetcher()
#     data = asyncio.run(instance.get_data())
#     print(data)