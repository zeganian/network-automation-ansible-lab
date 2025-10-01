#!/usr/bin/env python3
# Telegram Bot for Triggering Ansible Playbooks
# Best practice: Use async untuk scalability, handle errors gracefully.
# Install: pip install python-telegram-bot==21.0

import asyncio
import subprocess
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from ansible.module_utils.common.text import to_native  # Import Ansible utils jika perlu
import os

# Load vars from Ansible Vault? Simpan di env untuk simplicity.
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')  # Set env: export TELEGRAM_TOKEN=...
CHAT_ID = int(os.getenv('CHAT_ID'))  # Export CHAT_ID=...

PLAYBOOKS = {
    'install_nodejs': 'playbooks/install_nodejs.yml',
    'verify_connectivity': 'playbooks/verify_connectivity.yml',
    'basic_config': 'playbooks/basic_config.yml',
    'health_check': 'playbooks/health_check.yml',
    'backup_recovery': 'playbooks/backup_recovery.yml',
    'network_config': 'playbooks/network_config.yml',
    'compliance_audit': 'playbooks/compliance_audit.yml',
    'install_nginx': 'playbooks/install_nginx.yml',
}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Halo! Kirim /<playbook_name> untuk jalankan, e.g., /install_nodejs")

async def run_playbook(update: Update, context: ContextTypes.DEFAULT_TYPE, playbook_name: str):
    playbook_path = PLAYBOOKS.get(playbook_name)
    if not playbook_path:
        await update.message.reply_text(f"Playbook '{playbook_name}' tidak ditemukan!")
        return
    
    await update.message.reply_text(f"Memulai eksekusi {playbook_name}...")
    
    try:
        # Jalankan ansible-playbook dengan vault pass via env atau file
        cmd = [
            'ansible-playbook', playbook_path, '-i', 'inventory.ini',
            '--vault-id', '@prompt'  # Atau gunakan --vault-password-file
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        output = to_native(result.stdout) if 'to_native' in globals() else result.stdout
        await context.bot.send_message(chat_id=CHAT_ID, text=f"✅ Sukses: {playbook_name}\nOutput: {output[:500]}...")  # Truncate jika panjang
    except subprocess.CalledProcessError as e:
        error_msg = to_native(e.stderr) if 'to_native' in globals() else e.stderr
        await context.bot.send_message(chat_id=CHAT_ID, text=f"❌ Gagal: {playbook_name}\nError: {error_msg[:500]}...")
        await update.message.reply_text(f"Gagal jalankan {playbook_name}: {error_msg[:200]}...")

# Handlers untuk setiap command
async def install_nodejs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await run_playbook(update, context, 'install_nodejs')

# ... (Tambah handler serupa untuk setiap playbook, e.g., async def verify_connectivity(...))

def main():
    if not TELEGRAM_TOKEN:
        print("Set TELEGRAM_TOKEN env var!")
        return
    
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("install_nodejs", install_nodejs))
    app.add_handler(CommandHandler("verify_connectivity", verify_connectivity))
    # Tambah untuk yang lain: basic_config, health_check, dll.
    
    print("Bot berjalan... Tekan Ctrl+C untuk stop.")
    app.run_polling()

if __name__ == '__main__':
    main()