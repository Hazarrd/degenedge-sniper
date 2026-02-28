#!/usr/bin/env python3
"""
DegenEdge Sniper Bot
Listens to @TheDegenEdge channel for BSC token CA
Buys with ALL USDC in wallet instantly
Manual sell only - you choose when to exit
"""

import asyncio
import json
import os
import re
import requests
import subprocess
from datetime import datetime
from telethon import TelegramClient, events
from dotenv import load_dotenv

load_dotenv()

# Config
SESSION_NAME = os.getenv('DEGEN_SESSION', 'degen_edge_session')
CHANNEL_USERNAME = 'TheDegenEdge'  # https://t.me/TheDegenEdge
API_ID = int(os.getenv('TELEGRAM_API_ID', 35589298))
API_HASH = os.getenv('TELEGRAM_API_HASH', '714a286d638e9236cb75b1aa5af35bd2')

# BSC Config
RPC_URL_BSC = os.getenv('RPC_URL_BSC', 'https://bsc-dataseed.binance.org')
EVM_PRIVATE_KEY = os.getenv('EVM_PRIVATE_KEY')

# Token addresses
USDT_BSC = '0x55d398326f99059fF775485246999027B3197955'
WBNB_BSC = '0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c'

SLIPPAGE_BPS = 500  # 5% slippage for fast execution

PATTERNS = {
    'bsc_address': r'0x[a-fA-F0-9]{40}',
}


class DegenEdgeSniper:
    def __init__(self):
        self.client = None
        self.bought_tokens = {}  # Track bought positions for manual sell
        
        if not EVM_PRIVATE_KEY:
            print("❌ ERROR: EVM_PRIVATE_KEY not set!")
            print("   export EVM_PRIVATE_KEY='0x...'")
            exit(1)
        
        print("🔫 DegenEdge Sniper initialized")
        print(f"   Wallet: {self.get_wallet_address()}")
        print(f"   Target: @{CHANNEL_USERNAME}")
        
    def get_wallet_address(self):
        """Get wallet address from private key"""
        try:
            result = subprocess.run(
                ['node', '-e', f'const {{Wallet}} = require("ethers"); console.log(new Wallet("{EVM_PRIVATE_KEY}").address)'],
                capture_output=True, text=True, timeout=10, cwd='/root/.openclaw/workspace/fire-intern-v2'
            )
            return result.stdout.strip()
        except:
            return 'UNKNOWN'
    
    async def get_usdc_balance(self):
        """Get USDC balance in wallet"""
        try:
            wallet = self.get_wallet_address()
            
            script = f"""
const {{ ethers }} = require('ethers');
const provider = new ethers.JsonRpcProvider('{RPC_URL_BSC}');
const erc20Abi = ['function balanceOf(address) view returns (uint256)', 'function decimals() view returns (uint8)'];
const usdt = new ethers.Contract('{USDT_BSC}', erc20Abi, provider);
usdt.balanceOf('{wallet}').then(b => console.log('BALANCE:' + b.toString()));
"""
            with open('/tmp/check_balance.js', 'w') as f:
                f.write(script)
            
            result = subprocess.run(['node', '/tmp/check_balance.js'], 
                                  capture_output=True, text=True, timeout=10,
                                  cwd='/root/.openclaw/workspace/fire-intern-v2')
            
            for line in result.stdout.split('\n'):
                if line.startswith('BALANCE:'):
                    balance = int(line[8:])
                    # USDT has 18 decimals on BSC
                    return balance
            return 0
        except Exception as e:
            print(f"   Error checking balance: {e}")
            return 0
    
    async def start(self):
        self.client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
        
        @self.client.on(events.NewMessage(chats=CHANNEL_USERNAME))
        async def handler(event):
            await self.process_message(event)
        
        await self.client.start()
        me = await self.client.get_me()
        
        print("=" * 60)
        print(f"🎯 SNIPER ACTIVE")
        print("=" * 60)
        print(f"✅ Connected as {me.first_name}")
        print(f"📡 Monitoring: @{CHANNEL_USERNAME}")
        print(f"💰 Mode: ALL-IN (100% USDC)")
        print(f"⛽ Slippage: 5%")
        print(f"🛑 Sell: MANUAL ONLY")
        print("=" * 60)
        print("\n🔫 Waiting for CA drop...\n")
        
        # Check balance at start
        balance = await self.get_usdc_balance()
        print(f"💵 Current USDC Balance: {balance / 1e18:.2f} USDC")
        print("(Will use ALL on next CA)\n")
        
        await self.client.run_until_disconnected()
    
    async def process_message(self, event):
        """Process incoming message"""
        message = event.message
        text = message.text or ""
        
        if not text:
            return
        
        timestamp = datetime.now().isoformat()
        
        print(f"\n[{timestamp}] 📩 New message:")
        print(f"   {text[:150]}...")
        
        # Extract BSC addresses
        bsc_matches = re.findall(PATTERNS['bsc_address'], text)
        
        if not bsc_matches:
            return
        
        ca = bsc_matches[0]
        
        # Skip if already bought
        if ca in self.bought_tokens:
            print(f"   ⏭️ Already bought {ca[:20]}...")
            return
        
        print(f"\n🚨 BSC TOKEN DETECTED!")
        print(f"   CA: {ca}")
        print(f"   Chain: BSC")
        
        # ALL-IN BUY
        await self.execute_all_in_buy(ca)
    
    async def execute_all_in_buy(self, ca):
        """Buy with ALL USDC"""
        print(f"\n🔫 EXECUTING ALL-IN BUY...")
        
        # Get balance
        balance = await self.get_usdc_balance()
        
        if balance <= 0:
            print("   ❌ No USDC balance!")
            return
        
        print(f"   Balance: {balance / 1e18:.2f} USDC")
        print(f"   Buying: 100% (ALL-IN)")
        
        # Leave small amount for gas
        buy_amount = int(balance * 0.995)  # Use 99.5%, keep 0.5% for gas
        
        print(f"   Amount: {buy_amount} wei")
        
        # Execute via 1inch
        result = await self.execute_1inch_buy(ca, buy_amount)
        
        if result['success']:
            print(f"\n✅ BUY EXECUTED!")
            print(f"   TX: {result.get('tx_hash', 'UNKNOWN')}")
            print(f"   Token: {ca}")
            
            # Save position for manual sell
            self.bought_tokens[ca] = {
                'ca': ca,
                'chain': 'bsc',
                'buy_tx': result.get('tx_hash'),
                'amount': buy_amount,
                'timestamp': datetime.now().isoformat(),
                'status': 'BOUGHT'
            }
            
            self.save_position(ca, self.bought_tokens[ca])
            
            # Send alert
            await self.send_buy_alert(ca, result.get('tx_hash'), buy_amount)
            
        else:
            print(f"\n❌ BUY FAILED: {result.get('error')}")
    
    async def execute_1inch_buy(self, token_address, amount):
        """Execute buy using 1inch"""
        try:
            wallet = self.get_wallet_address()
            
            # 1inch v5.0 API (public)
            url = f"https://api.1inch.io/v5.0/56/swap"
            params = {
                'fromTokenAddress': USDT_BSC,
                'toTokenAddress': token_address,
                'amount': amount,
                'fromAddress': wallet,
                'slippage': SLIPPAGE_BPS / 100,
                'disableEstimate': 'true'  # Faster, skip estimation
            }
            
            print(f"   Getting swap data from 1inch...")
            response = requests.get(url, params=params, timeout=10)
            data = response.json()
            
            if 'tx' not in data:
                return {'success': False, 'error': data.get('error', 'NO_TX_DATA')}
            
            tx_data = data['tx']
            
            print(f"   Executing transaction...")
            return await self.send_transaction(tx_data)
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def send_transaction(self, tx_data):
        """Send transaction via ethers.js"""
        try:
            script = f"""
const {{ ethers }} = require('ethers');
async function main() {{
  const provider = new ethers.JsonRpcProvider('{RPC_URL_BSC}');
  const wallet = new ethers.Wallet('{EVM_PRIVATE_KEY}', provider);
  const tx = {{
    to: '{tx_data['to']}',
    data: '{tx_data['data']}',
    value: '{tx_data.get('value', '0')}',
    gasLimit: {tx_data.get('gas', 500000)}
  }};
  console.log('Sending...');
  const response = await wallet.sendTransaction(tx);
  console.log('TX_HASH:' + response.hash);
  await response.wait();
  console.log('CONFIRMED');
}}
main().catch(e => {{ console.error('ERROR:' + e.message); process.exit(1); }});
"""
            with open('/tmp/sniper_tx.js', 'w') as f:
                f.write(script)
            
            result = subprocess.run(['node', '/tmp/sniper_tx.js'],
                                  capture_output=True, text=True, timeout=60,
                                  cwd='/root/.openclaw/workspace/fire-intern-v2')
            
            if result.returncode == 0:
                tx_hash = None
                for line in result.stdout.split('\n'):
                    if line.startswith('TX_HASH:'):
                        tx_hash = line[8:].strip()
                        break
                return {'success': True, 'tx_hash': tx_hash or 'UNKNOWN'}
            else:
                return {'success': False, 'error': result.stderr}
                
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def save_position(self, ca, position):
        """Save position to file"""
        try:
            positions_file = '/root/.openclaw/workspace/degen_edge_positions.json'
            positions = {}
            if os.path.exists(positions_file):
                with open(positions_file, 'r') as f:
                    positions = json.load(f)
            
            positions[ca] = position
            
            with open(positions_file, 'w') as f:
                json.dump(positions, f, indent=2)
                
        except Exception as e:
            print(f"   Error saving position: {e}")
    
    async def send_buy_alert(self, ca, tx_hash, amount):
        """Send buy alert"""
        msg = f"""
🚨 **DEGENEDGE SNIPER - BUY EXECUTED!**

📊 Token: `{ca}`
🔗 Chain: BSC
💰 Amount: {amount / 1e18:.2f} USDC (ALL-IN)

📋 **To Sell (Manual):**
Use the sell script:
```
cd /root/.openclaw/workspace/fire-intern-v2
python3 manual_sell.py {ca}
```

🔗 TX: `{tx_hash}`
⏰ {datetime.now().strftime('%H:%M:%S')}
"""
        print("\n" + "=" * 60)
        print(msg)
        print("=" * 60)


async def main():
    sniper = DegenEdgeSniper()
    
    try:
        await sniper.start()
    except KeyboardInterrupt:
        print("\n\n👋 Sniper stopped")
    except Exception as e:
        print(f"\n❌ Error: {e}")


if __name__ == "__main__":
    asyncio.run(main())
