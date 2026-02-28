#!/usr/bin/env python3
"""Use bot token instead of phone number"""

from telethon import TelegramClient
import asyncio

API_ID = 35589298
API_HASH = "714a286d638e9236cb75b1aa5af35bd2"

async def main():
    print("You can use a BOT TOKEN instead of phone number!")
    print("\nGet a bot token from @BotFather:")
    print("1. Message @BotFather on Telegram")
    print("2. Send /newbot")
    print("3. Follow instructions")
    print("4. Copy the token (looks like: 123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11)")
    print("\nThen start the sniper with your bot token instead.")

asyncio.run(main())
