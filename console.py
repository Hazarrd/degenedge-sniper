#!/usr/bin/env python3
"""
DegenEdge Sniper - Telegram Control Console
Control the sniper bot from Telegram
"""

import asyncio
import json
import os
import subprocess
import signal
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '8548628662:AAGmFMxaW3wXBk_KErN9f0Z6-aiCi8yU2lc')
AUTHORIZED_USERS = set()

# Track sniper process
SNIPER_PROCESS = None
SNIPER_LOGS = []
MAX_LOG_LINES = 100


def is_authorized(user_id):
    return user_id in AUTHORIZED_USERS


# Command Handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start command"""
    user_id = update.effective_user.id
    AUTHORIZED_USERS.add(user_id)
    
    welcome = """🔫 **DegenEdge Sniper Console**

Control your sniper bot from Telegram!

**Commands:**
/status - Sniper status
/start_sniper - Start sniper bot
/stop_sniper - Stop sniper bot
/logs - View recent sniper logs
/positions - View bought tokens
/sell <CA> [pct] - Sell token manually
/balance - Check wallet balance
/help - Show all commands

**Quick Actions:**"""
    
    keyboard = [
        [InlineKeyboardButton("▶️ Start Sniper", callback_data='start_sniper'),
         InlineKeyboardButton("⏹ Stop Sniper", callback_data='stop_sniper')],
        [InlineKeyboardButton("📊 Status", callback_data='status'),
         InlineKeyboardButton("📜 Logs", callback_data='logs')],
        [InlineKeyboardButton("💰 Positions", callback_data='positions'),
         InlineKeyboardButton("💵 Balance", callback_data='balance')],
    ]
    
    await update.message.reply_text(welcome, reply_markup=InlineKeyboardMarkup(keyboard))


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show sniper status"""
    global SNIPER_PROCESS
    
    is_running = SNIPER_PROCESS is not None and SNIPER_PROCESS.poll() is None
    
    status_emoji = "🟢 RUNNING" if is_running else "🔴 STOPPED"
    
    # Check if EVM key is set
    evm_key = os.getenv('EVM_PRIVATE_KEY')
    key_status = "✅ Set" if evm_key else "❌ Not Set"
    
    msg = f"""📊 **Sniper Status**

**Status:** {status_emoji}
**EVM Key:** {key_status}
**Target:** @TheDegenEdge
**Chain:** BSC (1inch)
**Mode:** ALL-IN (100% USDC)

**Latest Logs:**
{get_recent_logs(5)}
"""
    
    await update.message.reply_text(msg)


async def start_sniper(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start the sniper bot"""
    global SNIPER_PROCESS
    
    # Check if already running
    if SNIPER_PROCESS and SNIPER_PROCESS.poll() is None:
        await update.message.reply_text("⚠️ Sniper is already running!")
        return
    
    # Check EVM key
    if not os.getenv('EVM_PRIVATE_KEY'):
        await update.message.reply_text(
            "❌ **EVM_PRIVATE_KEY not set!**\n\n"
            "Set it first:\n"
            "```\n"
            "export EVM_PRIVATE_KEY='0x...'\n"
            "```"
        )
        return
    
    # Start sniper
    try:
        SNIPER_PROCESS = subprocess.Popen(
            ['python3', 'sniper.py'],
            cwd='/root/.openclaw/workspace/fire-intern-v2',
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True
        )
        
        # Start log reader
        asyncio.create_task(read_sniper_logs(update.effective_user.id))
        
        await update.message.reply_text(
            "🚀 **Sniper Started!**\n\n"
            "Listening to @TheDegenEdge...\n"
            "Will buy ALL-IN when CA detected.\n\n"
            "Use /logs to view real-time output."
        )
        
    except Exception as e:
        await update.message.reply_text(f"❌ Failed to start: {e}")


async def stop_sniper(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Stop the sniper bot"""
    global SNIPER_PROCESS
    
    if not SNIPER_PROCESS or SNIPER_PROCESS.poll() is not None:
        await update.message.reply_text("⚠️ Sniper is not running.")
        return
    
    try:
        SNIPER_PROCESS.terminate()
        SNIPER_PROCESS.wait(timeout=5)
        SNIPER_PROCESS = None
        
        await update.message.reply_text("⏹ **Sniper Stopped.**")
        
    except Exception as e:
        await update.message.reply_text(f"❌ Error stopping: {e}")


async def logs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show sniper logs"""
    logs_text = get_recent_logs(20)
    
    msg = f"""📜 **Sniper Logs (last 20 lines)**

```
{logs_text}
```

_Last updated: {datetime.now().strftime('%H:%M:%S')}_
"""
    
    await update.message.reply_text(msg)


async def positions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show bought positions"""
    positions_file = '/root/.openclaw/workspace/degen_edge_positions.json'
    
    if not os.path.exists(positions_file):
        await update.message.reply_text("📭 **No positions yet.**")
        return
    
    try:
        with open(positions_file, 'r') as f:
            positions = json.load(f)
    except:
        await update.message.reply_text("❌ Error reading positions.")
        return
    
    if not positions:
        await update.message.reply_text("📭 **No positions yet.**")
        return
    
    msg = "💰 **Your Positions**\n\n"
    
    for ca, pos in positions.items():
        status = pos.get('status', 'UNKNOWN')
        amount = pos.get('amount', 0) / 1e18
        time = pos.get('timestamp', 'unknown')[11:16]
        
        emoji = "🟢" if status == 'BOUGHT' else "✅"
        
        msg += f"{emoji} `{ca[:20]}...`\n"
        msg += f"   Status: {status}\n"
        msg += f"   Amount: {amount:.2f} USDC\n"
        msg += f"   Time: {time}\n"
        msg += f"   Sell: `/sell {ca}`\n\n"
    
    await update.message.reply_text(msg)


async def sell_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Sell token manually"""
    args = context.args
    
    if len(args) < 1:
        await update.message.reply_text(
            "❌ **Usage:** `/sell <CA> [percentage]`\n\n"
            "Examples:\n"
            "`/sell 0x123...abc` - Sell 100%\n"
            "`/sell 0x123...abc 50` - Sell 50%"
        )
        return
    
    ca = args[0]
    percentage = int(args[1]) if len(args) > 1 else 100
    
    await update.message.reply_text(
        f"🔄 **Selling {percentage}%...**\n"
        f"Token: `{ca[:20]}...`\n\n"
        f"⏳ Executing..."
    )
    
    # Run sell script
    try:
        result = subprocess.run(
            ['python3', 'manual_sell.py', ca, str(percentage)],
            cwd='/root/.openclaw/workspace/fire-intern-v2',
            capture_output=True,
            text=True,
            timeout=120
        )
        
        output = result.stdout[-3000:] if len(result.stdout) > 3000 else result.stdout
        
        if result.returncode == 0:
            await update.message.reply_text(
                f"✅ **Sell Executed!**\n\n"
                f"```\n{output}\n```"
            )
        else:
            await update.message.reply_text(
                f"❌ **Sell Failed:**\n\n"
                f"```\n{result.stderr[-1000:]}\n```"
            )
            
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")


async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Check wallet balance"""
    # Run balance check
    try:
        result = subprocess.run(
            ['node', '-e', '''
const { ethers } = require('ethers');
const provider = new ethers.JsonRpcProvider('https://bsc-dataseed.binance.org');
const wallet = new ethers.Wallet(process.env.EVM_PRIVATE_KEY || '0x0', provider);
const usdt = new ethers.Contract('0x55d398326f99059fF775485246999027B3197955', 
    ['function balanceOf(address) view returns (uint256)', 'function decimals() view returns (uint8)'], provider);
Promise.all([wallet.getAddress(), provider.getBalance(wallet.address), usdt.balanceOf(wallet.address)])
    .then(([addr, bnb, usdt]) => {
        console.log('ADDRESS:' + addr);
        console.log('BNB:' + (bnb / 1e18).toFixed(4));
        console.log('USDT:' + (usdt / 1e18).toFixed(2));
    });
'''],
            cwd='/root/.openclaw/workspace/fire-intern-v2',
            capture_output=True,
            text=True,
            timeout=10,
            env={**os.environ, 'EVM_PRIVATE_KEY': os.getenv('EVM_PRIVATE_KEY', '0x0')}
        )
        
        output = result.stdout.strip()
        await update.message.reply_text(
            f"💵 **Wallet Balance**\n\n"
            f"```\n{output}\n```"
        )
        
    except Exception as e:
        await update.message.reply_text(f"❌ Error checking balance: {e}")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show help"""
    help_text = """🔫 **DegenEdge Sniper Console**

**Control Commands:**
/start_sniper - Start sniper bot
/stop_sniper - Stop sniper bot
/status - Check sniper status
/logs - View real-time logs

**Info Commands:**
/positions - View bought tokens
/balance - Check wallet balance
/sell - Sell tokens manually

**Setup:**
Before starting, set your BSC key:
```
export EVM_PRIVATE_KEY="0x..."
```

**How it works:**
1. Start sniper with /start_sniper
2. Bot listens to @TheDegenEdge
3. When CA dropped → Buys ALL-IN
4. Use /sell to exit manually
"""
    
    await update.message.reply_text(help_text)


# Callback handlers
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle inline buttons"""
    query = update.callback_query
    await query.answer()
    
    action = query.data
    
    if action == 'start_sniper':
        await start_sniper(update, context)
    elif action == 'stop_sniper':
        await stop_sniper(update, context)
    elif action == 'status':
        await status(update, context)
    elif action == 'logs':
        await logs(update, context)
    elif action == 'positions':
        await positions(update, context)
    elif action == 'balance':
        await balance(update, context)


# Helper functions
def get_recent_logs(n=20):
    """Get recent log lines"""
    return '\n'.join(SNIPER_LOGS[-n:]) if SNIPER_LOGS else "No logs yet."


async def read_sniper_logs(user_id):
    """Background task to read sniper output"""
    global SNIPER_PROCESS, SNIPER_LOGS
    
    if not SNIPER_PROCESS:
        return
    
    for line in iter(SNIPER_PROCESS.stdout.readline, ''):
        if not line:
            break
        
        line = line.strip()
        SNIPER_LOGS.append(line)
        
        # Keep only last N lines
        if len(SNIPER_LOGS) > MAX_LOG_LINES:
            SNIPER_LOGS = SNIPER_LOGS[-MAX_LOG_LINES:]
        
        # Check for buy alerts
        if "BUY EXECUTED" in line or "🚨 BSC TOKEN DETECTED" in line:
            # Could send alert to user here
            pass
    
    SNIPER_PROCESS.stdout.close()


async def main():
    """Start the console bot"""
    if BOT_TOKEN == 'your_bot_token_here':
        print("❌ Set TELEGRAM_BOT_TOKEN in .env")
        return
    
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("status", status))
    application.add_handler(CommandHandler("start_sniper", start_sniper))
    application.add_handler(CommandHandler("stop_sniper", stop_sniper))
    application.add_handler(CommandHandler("logs", logs))
    application.add_handler(CommandHandler("positions", positions))
    application.add_handler(CommandHandler("sell", sell_command))
    application.add_handler(CommandHandler("balance", balance))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CallbackQueryHandler(button_callback))
    
    print("🤖 DegenEdge Console Bot starting...")
    
    await application.initialize()
    await application.start()
    await application.updater.start_polling()
    
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        if SNIPER_PROCESS:
            SNIPER_PROCESS.terminate()
        await application.updater.stop()
        await application.stop()
        await application.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
