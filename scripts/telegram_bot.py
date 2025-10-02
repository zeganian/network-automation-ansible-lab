#!/usr/bin/env python3
import os
import subprocess
from pathlib import Path
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# --- Konfigurasi dasar ---
BASE_DIR = Path(__file__).resolve().parent.parent  # root project
INVENTORY = BASE_DIR / "Inventory" / "hosts.ini"

# Mapping command Telegram ke playbook
PLAYBOOKS = {
    "install_nginx": BASE_DIR / "Playbooks" / "install_nginx.yml",
    "remove_nginx": BASE_DIR / "Playbooks" / "uninstall_nginx.yml",
    "verify_connectivity": BASE_DIR / "Playbooks" / "verify_connectivity.yml"
}

# Token, Chat ID, dan sudo password dari environment
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
BECOME_PASS = os.getenv("BECOME_PASS")  # <--- tambahkan ini

if not TOKEN or not CHAT_ID:
    raise EnvironmentError("❌ TELEGRAM_TOKEN dan CHAT_ID harus di-set di environment!")

# --- Fungsi handler command ---
async def run_playbook(update: Update, context: ContextTypes.DEFAULT_TYPE):
    command = update.message.text.strip("/")

    if command in PLAYBOOKS:
        playbook_path = PLAYBOOKS[command]

        cmd = [
            "ansible-playbook",
            str(playbook_path),
            "-i", str(INVENTORY),
        ]

        # jika ada sudo password, kita pakai --extra-vars
        if BECOME_PASS:
            cmd += ["--extra-vars", f"ansible_become_pass={BECOME_PASS}"]
        else:
            cmd.append("--ask-become-pass")

        await update.message.reply_text(f"▶️ Menjalankan playbook: {command} ...")

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True
            )
            output = result.stdout.strip()
            # batasi panjang agar chat Telegram tidak kepanjangan
            if len(output) > 700:
                output = output[:700] + "\n...\n(log dipotong)"
            await update.message.reply_text(f"✅ Sukses: {command}\n\n{output}")
        except subprocess.CalledProcessError as e:
            error = e.stderr.strip()
            if len(error) > 700:
                error = error[:700] + "\n...\n(log dipotong)"
            await update.message.reply_text(f"❌ Gagal: {command}\n\n{error}")
    else:
        await update.message.reply_text("⚠️ Command tidak dikenal.")

# --- Main Bot ---
def main():
    app = Application.builder().token(TOKEN).build()

    # Register semua command playbook
    for cmd in PLAYBOOKS.keys():
        app.add_handler(CommandHandler(cmd, run_playbook))

    print("🤖 Bot berjalan... (CTRL+C untuk berhenti)")
    app.run_polling()

if __name__ == "__main__":
    main()
