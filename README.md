# DegenEdge Sniper Bot

**Fast BSC sniper for @TheDegenEdge token launches.**

Listens to Telegram channel → Detects CA → Buys ALL-IN instantly → Manual sell when you want.

## ⚡ Quick Start

```bash
# 1. Clone & setup
git clone https://github.com/Hazarrd/degenedge-sniper.git
cd degenedge-sniper
pip install -r requirements.txt
npm install

# 2. Configure
cp .env.example .env
nano .env  # Add your keys

# 3. Test Telegram login
python3 -c "from telethon import TelegramClient; c=TelegramClient('session', 35589298, '714a286d638e9236cb75b1aa5af35bd2'); c.start()"

# 4. Start sniper
python3 bot.py
```

## 🎯 Features

- **ALL-IN Buy**: Uses 100% of USDC balance
- **1inch Integration**: Best swap rates on BSC
- **Real-time**: Sub-second detection to execution
- **Manual Sell**: You control when to exit
- **Telegram Console**: Control from your phone

## 🔧 Configuration (.env)

```
# Required
EVM_PRIVATE_KEY=0x...                    # BSC wallet private key
TELEGRAM_API_ID=35589298                 # From my.telegram.org
TELEGRAM_API_HASH=714a286d638e9236cb75b1aa5af35bd2

# Optional
RPC_URL_BSC=https://bsc-dataseed.binance.org
TARGET_CHANNEL=TheDegenEdge
SLIPPAGE_BPS=500                         # 5%
```

## 🚀 Usage

**Start sniper:**
```bash
python3 bot.py
```

**Or use Telegram console:**
```bash
python3 console.py
```

**Sell manually:**
```bash
# Sell 100%
python3 sell.py 0xTOKEN_CA

# Sell 50%
python3 sell.py 0xTOKEN_CA 50

# List positions
python3 sell.py list
```

## 📱 Telegram Console Commands

- `/start_sniper` — Start sniper
- `/stop_sniper` — Stop sniper
- `/status` — Check status
- `/logs` — View logs
- `/positions` — See bought tokens
- `/sell <CA>` — Sell token
- `/balance` — Check wallet

## ⚠️ Risk Warning

- This bot spends ALL your USDC on every CA detected
- Make sure you have the correct channel set
- Test with small amounts first
- You are responsible for your trades

## License

MIT
