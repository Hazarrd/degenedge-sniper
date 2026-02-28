#!/usr/bin/env python3
"""Quick login script - run this and enter your code"""

from telethon import TelegramClient

API_ID = 35589298
API_HASH = "714a286d638e9236cb75b1aa5af35bd2"

print("=" * 50)
print("DegenEdge Sniper - Telegram Login")
print("=" * 50)
print("\nPhone: +2349116809686")
print("Waiting for code...\n")

client = TelegramClient('degen_sniper', API_ID, API_HASH)

async def main():
    await client.start(phone='+2349116809686')
    me = await client.get_me()
    print(f"\n✅ SUCCESS! Logged in as {me.first_name}")
    print("✅ Session saved to 'degen_sniper.session'")
    print("\nYou can now run: python3 bot.py")

with client:
    client.loop.run_until_complete(main())
