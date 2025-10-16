import os
import subprocess
import time
import logging
import telegram
from telegram import Bot
from telegram.ext import Updater, CommandHandler

# Hanya matikan logging apscheduler saja
logging.getLogger('apscheduler').setLevel(logging.CRITICAL)

try:
    from config import TELEGRAM_TOKEN, CHAT_ID, PROJECT_PATH, PLAYBOOK_PATH, REMOVE_PLAYBOOK_PATH, INVENTORY_PATH
except ImportError:
    print("Error: File config.py tidak ditemukan!")
    exit(1)

def start(update, context):
    if update and update.message:
        update.message.reply_text(
            "Network Automation Bot Siap!\n\n"
            "Perintah:\n"
            "/install_nginx - Install Nginx\n"
            "/remove_nginx - Hapus Nginx\n"
            "/status - Status koneksi"
        )

def status(update, context):
    if not update or not update.message:
        return

    try:
        result = subprocess.run(
            ["ansible", "lab_nodes", "-i", INVENTORY_PATH, "-m", "ping"],
            capture_output=True,
            text=True,
            cwd=PROJECT_PATH,
            timeout=30
        )
        output = result.stdout.strip()
        update.message.reply_text(f"Status:\n```{output}```", parse_mode="Markdown")
    except Exception as e:
        update.message.reply_text(f"Error: {str(e)}")

def install_nginx(update, context):
    if not update or not update.message:
        return

    update.message.reply_text("Memulai instalasi Nginx...")

    try:
        start_time = time.time()
        result = subprocess.run(
            ["ansible-playbook", "-i", INVENTORY_PATH, PLAYBOOK_PATH],
            capture_output=True,
            text=True,
            cwd=PROJECT_PATH,
            timeout=300
        )
        execution_time = time.time() - start_time

        if result.returncode == 0:
            message = f"Instalasi Nginx Berhasil!\nWaktu: {execution_time:.1f} detik\n\n"

            # Tampilkan output lengkap Ansible
            lines = result.stdout.split('\n')
            important_lines = [line for line in lines if any(x in line for x in ['TASK', 'PLAY', 'changed=', 'ok=', 'failed=', 'unreachable=', 'PLAY RECAP'])]
            if important_lines:
                message += "Output Ansible:\n```\n" + "\n".join(important_lines) + "\n```"
            else:
                message += result.stdout[-1500:] if result.stdout else "Tidak ada output"
        else:
            message = f"Instalasi Nginx Gagal!\nKode: {result.returncode}\n\n"
            message += "Error:\n```\n" + (result.stderr if result.stderr else result.stdout) + "\n```"

        update.message.reply_text(message, parse_mode="Markdown")
        send_notification(f"INSTALASI BERHASIL - Waktu: {execution_time:.1f}s")

    except subprocess.TimeoutExpired:
        update.message.reply_text("Timeout: Proses terlalu lama")
        send_notification("INSTALASI TIMEOUT")
    except Exception as e:
        update.message.reply_text(f"Error: {str(e)}")
        send_notification(f"INSTALASI ERROR: {str(e)}")

def remove_nginx(update, context):
    if not update or not update.message:
        return

    update.message.reply_text("Memulai penghapusan Nginx...")

    try:
        start_time = time.time()
        result = subprocess.run(
            ["ansible-playbook", "-i", INVENTORY_PATH, REMOVE_PLAYBOOK_PATH],
            capture_output=True,
            text=True,
            cwd=PROJECT_PATH,
            timeout=300
        )
        execution_time = time.time() - start_time

        if result.returncode == 0:
            message = f"Penghapusan Nginx Berhasil!\nWaktu: {execution_time:.1f} detik\n\n"

            # Tampilkan output lengkap Ansible
            lines = result.stdout.split('\n')
            important_lines = [line for line in lines if any(x in line for x in ['TASK', 'PLAY', 'changed=', 'ok=', 'failed=', 'unreachable=', 'PLAY RECAP'])]
            if important_lines:
                message += "Output Ansible:\n```\n" + "\n".join(important_lines) + "\n```"
            else:
                message += result.stdout[-1500:] if result.stdout else "Tidak ada output"
        else:
            message = f"Penghapusan Nginx Gagal!\nKode: {result.returncode}\n\n"
            message += "Error:\n```\n" + (result.stderr if result.stderr else result.stdout) + "\n```"

        update.message.reply_text(message, parse_mode="Markdown")
        send_notification(f"PENGHAPUSAN BERHASIL - Waktu: {execution_time:.1f}s")

    except subprocess.TimeoutExpired:
        update.message.reply_text("Timeout: Proses terlalu lama")
        send_notification("PENGHAPUSAN TIMEOUT")
    except Exception as e:
        update.message.reply_text(f"Error: {str(e)}")
        send_notification(f"PENGHAPUSAN ERROR: {str(e)}")

def send_notification(message):
    try:
        bot = Bot(token=TELEGRAM_TOKEN)
        bot.send_message(chat_id=CHAT_ID, text=message)
    except Exception as e:
        print(f"Gagal notifikasi: {e}")

def error_handler(update, context):
    # Ignore connection errors
    error = context.error
    if "Connection aborted" not in str(error) and "RemoteDisconnected" not in str(error):
        print(f"Error: {error}")

def main():
    if TELEGRAM_TOKEN == "ISI_DENGAN_TOKEN_ASLI_ANDA" or not TELEGRAM_TOKEN:
        print("ERROR: Token belum dikonfigurasi!")
        return

    for name, path in [("Playbook Install", PLAYBOOK_PATH),
                      ("Playbook Remove", REMOVE_PLAYBOOK_PATH),
                      ("Inventory", INVENTORY_PATH)]:
        if not os.path.exists(path):
            print(f"ERROR: {name} tidak ditemukan: {path}")
            return

    print("Config valid")
    print(f"Project: {PROJECT_PATH}")

    try:
        print("Testing connection...")
        bot = Bot(token=TELEGRAM_TOKEN)
        bot_info = bot.get_me()
        print(f"Bot: {bot_info.first_name} (@{bot_info.username})")

        updater = Updater(
            token=TELEGRAM_TOKEN,
            use_context=True,
            request_kwargs={
                'read_timeout': 30,
                'connect_timeout': 30,
            }
        )

        dp = updater.dispatcher

        dp.add_handler(CommandHandler("start", start))
        dp.add_handler(CommandHandler("status", status))
        dp.add_handler(CommandHandler("install_nginx", install_nginx))
        dp.add_handler(CommandHandler("remove_nginx", remove_nginx))

        dp.add_error_handler(error_handler)

        print("Bot berjalan...")
        print("Commands: /install_nginx, /remove_nginx, /status")

        updater.start_polling(drop_pending_updates=True)
        updater.idle()

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
