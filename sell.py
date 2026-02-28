#!/usr/bin/env python3
"""
Manual Sell Script for DegenEdge Sniper
Sell your BSC tokens manually when you're ready
"""

import json
import os
import requests
import subprocess
import sys
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

RPC_URL_BSC = os.getenv('RPC_URL_BSC', 'https://bsc-dataseed.binance.org')
EVM_PRIVATE_KEY = os.getenv('EVM_PRIVATE_KEY')
USDT_BSC = '0x55d398326f99059fF775485246999027B3197955'


def get_wallet_address():
    """Get wallet address"""
    try:
        result = subprocess.run(
            ['node', '-e', f'const {{Wallet}} = require("ethers"); console.log(new Wallet("{EVM_PRIVATE_KEY}").address)'],
            capture_output=True, text=True, timeout=10,
            cwd='/root/.openclaw/workspace/fire-intern-v2'
        )
        return result.stdout.strip()
    except:
        return None


def get_token_balance(token_ca, wallet):
    """Get token balance"""
    try:
        script = f"""
const {{ ethers }} = require('ethers');
const provider = new ethers.JsonRpcProvider('{RPC_URL_BSC}');
const erc20Abi = ['function balanceOf(address) view returns (uint256)', 'function decimals() view returns (uint8)'];
const token = new ethers.Contract('{token_ca}', erc20Abi, provider);
token.balanceOf('{wallet}').then(b => console.log('BALANCE:' + b.toString()));
"""
        with open('/tmp/check_token_balance.js', 'w') as f:
            f.write(script)
        
        result = subprocess.run(['node', '/tmp/check_token_balance.js'],
                              capture_output=True, text=True, timeout=10,
                              cwd='/root/.openclaw/workspace/fire-intern-v2')
        
        for line in result.stdout.split('\n'):
            if line.startswith('BALANCE:'):
                return int(line[8:])
        return 0
    except Exception as e:
        print(f"Error checking balance: {e}")
        return 0


def sell_token(token_ca, percentage=100):
    """Sell token via 1inch"""
    wallet = get_wallet_address()
    if not wallet:
        print("❌ Could not get wallet address")
        return
    
    print(f"📊 Checking balance for {token_ca[:20]}...")
    balance = get_token_balance(token_ca, wallet)
    
    if balance <= 0:
        print("❌ No token balance!")
        return
    
    sell_amount = int(balance * percentage / 100)
    
    print(f"💰 Balance: {balance}")
    print(f"💰 Selling: {sell_amount} ({percentage}%)")
    
    # Get 1inch swap data
    print(f"🔄 Getting swap data from 1inch...")
    
    url = f"https://api.1inch.io/v5.0/56/swap"
    params = {
        'fromTokenAddress': token_ca,
        'toTokenAddress': USDT_BSC,
        'amount': sell_amount,
        'fromAddress': wallet,
        'slippage': 5,  # 5%
        'disableEstimate': 'true'
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        
        if 'tx' not in data:
            print(f"❌ 1inch error: {data.get('error', 'Unknown')}")
            return
        
        tx_data = data['tx']
        
        print(f"⛽ Executing sell transaction...")
        
        # Execute transaction
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
  console.log('Sending sell tx...');
  const response = await wallet.sendTransaction(tx);
  console.log('TX_HASH:' + response.hash);
  await response.wait();
  console.log('SELL_CONFIRMED');
}}
main().catch(e => {{ console.error('ERROR:' + e.message); process.exit(1); }});
"""
        with open('/tmp/sell_tx.js', 'w') as f:
            f.write(script)
        
        result = subprocess.run(['node', '/tmp/sell_tx.js'],
                              capture_output=True, text=True, timeout=60,
                              cwd='/root/.openclaw/workspace/fire-intern-v2')
        
        if result.returncode == 0:
            tx_hash = None
            for line in result.stdout.split('\n'):
                if line.startswith('TX_HASH:'):
                    tx_hash = line[8:].strip()
            
            print(f"\n✅ SELL EXECUTED!")
            print(f"   TX: {tx_hash}")
            print(f"   Sold: {percentage}% of tokens")
            
            # Update position file
            update_position(token_ca, tx_hash, percentage)
            
        else:
            print(f"❌ Sell failed: {result.stderr}")
            
    except Exception as e:
        print(f"❌ Error: {e}")


def update_position(ca, sell_tx, percentage):
    """Update position status"""
    try:
        positions_file = '/root/.openclaw/workspace/degen_edge_positions.json'
        if not os.path.exists(positions_file):
            return
        
        with open(positions_file, 'r') as f:
            positions = json.load(f)
        
        if ca in positions:
            positions[ca]['sell_tx'] = sell_tx
            positions[ca]['sell_percentage'] = percentage
            positions[ca]['sell_time'] = datetime.now().isoformat()
            positions[ca]['status'] = 'SOLD'
            
            with open(positions_file, 'w') as f:
                json.dump(positions, f, indent=2)
                
    except Exception as e:
        print(f"Error updating position: {e}")


def list_positions():
    """List all positions"""
    positions_file = '/root/.openclaw/workspace/degen_edge_positions.json'
    
    if not os.path.exists(positions_file):
        print("No positions found")
        return
    
    with open(positions_file, 'r') as f:
        positions = json.load(f)
    
    if not positions:
        print("No positions found")
        return
    
    print("\n📋 Your Positions:")
    print("=" * 60)
    
    for ca, pos in positions.items():
        status = pos.get('status', 'UNKNOWN')
        buy_tx = pos.get('buy_tx', 'N/A')[:16]
        amount = pos.get('amount', 0) / 1e18
        
        print(f"\nToken: {ca}")
        print(f"Status: {status}")
        print(f"Buy Amount: {amount:.2f} USDC")
        print(f"Buy TX: {buy_tx}...")
        
        if status == 'SOLD':
            sell_tx = pos.get('sell_tx', 'N/A')[:16]
            sell_pct = pos.get('sell_percentage', 0)
            print(f"Sold: {sell_pct}%")
            print(f"Sell TX: {sell_tx}...")
        else:
            print(f"To sell: python3 manual_sell.py {ca}")
    
    print("=" * 60)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("DegenEdge Manual Sell")
        print("\nUsage:")
        print(f"  python3 {sys.argv[0]} <token_ca> [percentage]")
        print(f"  python3 {sys.argv[0]} list")
        print("\nExamples:")
        print(f"  python3 {sys.argv[0]} 0x123...abc           # Sell 100%")
        print(f"  python3 {sys.argv[0]} 0x123...abc 50        # Sell 50%")
        print(f"  python3 {sys.argv[0]} list                  # List all positions")
        sys.exit(1)
    
    if sys.argv[1] == 'list':
        list_positions()
    else:
        token_ca = sys.argv[1]
        percentage = int(sys.argv[2]) if len(sys.argv) > 2 else 100
        sell_token(token_ca, percentage)
