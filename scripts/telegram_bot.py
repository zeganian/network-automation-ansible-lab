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
    from config import (
        TELEGRAM_TOKEN, CHAT_ID, PROJECT_PATH,
        WINDOWS_INVENTORY_PATH, WINDOWS_SOFTWARE_PLAYBOOK
    )
except ImportError as e:
    print(f"❌ Error: File config.py tidak ditemukan! {e}")
    exit(1)

def start(update, context):
    if update and update.message:
        update.message.reply_text(
            "🤖 WINDOWS LAB AUTOMATION BOT\n\n"
            "📋 PERINTAH YANG TERSEDIA:\n"
            "/start - Menu utama\n"
            "/lab_status - Status PC Lab\n"
            "/windows_ping - Test koneksi Windows PCs\n"
            "/install_software - Install software umum\n\n"
            "💡 Gunakan untuk manage Windows Lab PCs"
        )

def lab_status(update, context):
    """Status semua Windows PC dengan handling PC offline"""
    if not update or not update.message:
        return

    update.message.reply_text("🔍 Scanning semua PC di lab...")

    try:
        # 1. GET HOSTS DARI INVENTORY (tanpa test koneksi dulu)
        inventory_hosts = {}
        with open(WINDOWS_INVENTORY_PATH, 'r') as f:
            lines = f.readlines()
            in_windows_section = False

            for line in lines:
                line = line.strip()
                if line == '[windows_lab]':
                    in_windows_section = True
                    continue
                elif line.startswith('['):
                    in_windows_section = False
                    continue

                if in_windows_section and line and not line.startswith((';', '#')):
                    parts = line.split()
                    if parts:
                        host_name = parts[0]
                        ip = "N/A"
                        for part in parts:
                            if part.startswith('ansible_host='):
                                ip = part.split('=')[1]
                                break
                        inventory_hosts[host_name] = ip

        # 2. TEST KONEKSI DENGAN TIMEOUT LEBIH PENDEK
        message = "🖥️ *WINDOWS LAB STATUS*\n"
        message += "══════════════════════════════════════\n\n"

        if inventory_hosts:
            message += f"📋 *DI INVENTORY:* {len(inventory_hosts)} PC\n\n"

            # Test koneksi per PC dengan timeout pendek
            online_pcs = []
            offline_pcs = []

            for host_name, ip in sorted(inventory_hosts.items()):
                try:
                    # Test individual PC dengan timeout cepat
                    ping_result = subprocess.run(
                        ["ansible", host_name, "-i", WINDOWS_INVENTORY_PATH, "-m", "win_ping"],
                        capture_output=True,
                        text=True,
                        cwd=PROJECT_PATH,
                        timeout=10  # Timeout pendek per PC
                    )

                    if ping_result.returncode == 0:
                        online_pcs.append(host_name)
                        message += f"🟢 {host_name}\n"
                        message += f"   📡 `{ip}`\n"
                    else:
                        offline_pcs.append(host_name)
                        message += f"🔴 {host_name}\n"
                        message += f"   📡 `{ip}`\n"

                except subprocess.TimeoutExpired:
                    offline_pcs.append(host_name)
                    message += f"🔴 {host_name} (Timeout)\n"
                    message += f"   📡 `{ip}`\n"
                except Exception:
                    offline_pcs.append(host_name)
                    message += f"🔴 {host_name} (Error)\n"
                    message += f"   📡 `{ip}`\n"

                message += "\n"

            # SUMMARY
            message += "══════════════════════════════════════\n"
            message += f"*📊 REAL-TIME STATUS:*\n"
            message += f"🟢 Online: `{len(online_pcs)}` PC\n"
            message += f"🔴 Offline: `{len(offline_pcs)}` PC\n"
            message += f"📟 Total: `{len(inventory_hosts)}` PC\n\n"

        else:
            message += "❌ *Tidak ada PC terdeteksi di inventory!*\n\n"

        # QUICK ACTIONS
        message += "*🚀 QUICK ACTIONS:*\n"
        message += "`/windows_ping` - Test koneksi detail\n"
        message += "`/install_software` - Install aplikasi (hanya PC online)\n"
        message += "`/start` - Menu utama"

        update.message.reply_text(message, parse_mode="Markdown")

    except Exception as e:
        update.message.reply_text(f"❌ *Error:* `{str(e)}`\n\n💡 Periksa file inventory dan koneksi network.", parse_mode="Markdown")

def windows_ping(update, context):
    """Test koneksi ke semua Windows PCs dengan handling PC offline"""
    if not update or not update.message:
        return

    update.message.reply_text("🔄 Testing koneksi ke Windows PCs...")

    try:
        start_time = time.time()

        # Gunakan --one-line untuk output yang lebih clean
        result = subprocess.run(
            ["ansible", "windows_lab", "-i", WINDOWS_INVENTORY_PATH, "-m", "win_ping", "--one-line"],
            capture_output=True,
            text=True,
            cwd=PROJECT_PATH,
            timeout=60
        )
        execution_time = time.time() - start_time

        message = f"📡 *WINDOWS PING TEST*\n"
        message += f"⏱️ Waktu: {execution_time:.1f}s\n\n"

        if result.returncode == 0 or result.returncode == 4:  # 4 = some hosts unreachable
            lines = result.stdout.split('\n')
            online_pcs = []
            offline_pcs = []

            for line in lines:
                if 'SUCCESS' in line:
                    pc_name = line.split('|')[0].strip()
                    online_pcs.append(pc_name)
                elif 'UNREACHABLE' in line:
                    pc_name = line.split('|')[0].strip()
                    offline_pcs.append(pc_name)

            message += f"✅ *ONLINE:* {len(online_pcs)} PC\n"
            for pc in sorted(online_pcs):
                message += f"   • {pc}\n"

            if offline_pcs:
                message += f"\n❌ *OFFLINE:* {len(offline_pcs)} PC\n"
                for pc in sorted(offline_pcs):
                    message += f"   • {pc}\n"

            message += f"\n📊 Total: {len(online_pcs) + len(offline_pcs)} PC"

        else:
            message += "❌ *GAGAL TESTING*\n"
            message += f"Kode Error: `{result.returncode}`\n\n"
            message += "💡 *Solusi:*\n"
            message += "• Periksa file inventory\n"
            message += "• Pastikan beberapa PC online\n"
            message += "• Cek koneksi network"

        update.message.reply_text(message, parse_mode="Markdown")

    except subprocess.TimeoutExpired:
        update.message.reply_text("⏰ *Timeout: Testing terlalu lama*\n\nBeberapa PC mungkin sedang booting atau offline.", parse_mode="Markdown")
    except Exception as e:
        update.message.reply_text(f"❌ *Error:* `{str(e)}`", parse_mode="Markdown")

def install_software(update, context):
    """Install common software dengan detailed reporting"""
    if not update or not update.message:
        return

    try:
        update.message.reply_text("🔍 Memulai proses instalasi...")

        # Validasi file
        if not os.path.exists(WINDOWS_SOFTWARE_PLAYBOOK):
            update.message.reply_text("❌ File playbook tidak ditemukan!", parse_mode="Markdown")
            return

        # Check PC online
        update.message.reply_text("🌐 Checking koneksi PC...")
        ping_result = subprocess.run(
            ["ansible", "windows_lab", "-i", WINDOWS_INVENTORY_PATH, "-m", "win_ping", "--one-line"],
            capture_output=True,
            text=True,
            cwd=PROJECT_PATH,
            timeout=30
        )

        online_pcs = []
        if ping_result.returncode == 0 or ping_result.returncode == 4:
            for line in ping_result.stdout.split('\n'):
                if 'SUCCESS' in line:
                    pc_name = line.split('|')[0].strip()
                    online_pcs.append(pc_name)

        if not online_pcs:
            update.message.reply_text("❌ Tidak ada PC yang online!", parse_mode="Markdown")
            return

        update.message.reply_text(f"🚀 Memulai instalasi ke {len(online_pcs)} PC...\n⏳ Proses mungkin memakan waktu 10-20 menit...")

        start_time = time.time()
        result = subprocess.run(
            ["ansible-playbook", "-i", WINDOWS_INVENTORY_PATH, WINDOWS_SOFTWARE_PLAYBOOK, "--limit", ",".join(online_pcs)],
            capture_output=True,
            text=True,
            cwd=PROJECT_PATH,
            timeout=2400  # 40 menit
        )
        execution_time = time.time() - start_time

        # PROCESS RESULTS
        message = f"📦 *HASIL INSTALASI SOFTWARE*\n"
        message += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        message += f"⏱️ Waktu: {execution_time:.1f}s\n"
        message += f"🖥️ PC Target: {len(online_pcs)}\n\n"

        if result.returncode == 0:
            message += "✅ *SEMUA SOFTWARE BERHASIL DIINSTALL!*\n\n"
            message += "📋 Software yang terinstall:\n"
            message += "• 🌐 Google Chrome\n• 🦊 Firefox\n• 💻 VS Code\n• 🎬 VLC\n• 📝 Notepad++\n• 🗜️ 7-Zip\n• 🐍 Python\n• 🔧 Git\n"

        elif result.returncode == 4:  # Some failures
            message += "⚠️ *SEBAGIAN SOFTWARE BERHASIL DIINSTALL*\n\n"

            # Parse output untuk lihat apa yang berhasil/gagal
            lines = result.stdout.split('\n')
            installed_software = []
            failed_software = []

            software_map = {
                'googlechrome': 'Google Chrome',
                'firefox': 'Firefox',
                'vscode': 'VS Code',
                'vlc': 'VLC',
                'notepadplusplus': 'Notepad++',
                '7zip': '7-Zip',
                'python': 'Python',
                'git': 'Git'
            }

            for line in lines:
                for sw_key, sw_name in software_map.items():
                    if f'Install {sw_key}' in line and 'ok=' in line:
                        if 'changed=1' in line:
                            installed_software.append(sw_name)
                        elif 'failed=' in line and 'failed=0' not in line:
                            failed_software.append(sw_name)

            if installed_software:
                message += "✅ *Berhasil:*\n"
                for sw in installed_software:
                    message += f"• {sw}\n"

            if failed_software:
                message += "\n❌ *Gagal:*\n"
                for sw in failed_software:
                    message += f"• {sw}\n"

            message += f"\n💡 *PC baru mungkin butuh:*\n- Install Chocolatey manual\n- Restart setelah instalasi\n- Koneksi internet stabil"

        else:
    message += "❌ *INSTALASI GAGAL!*\n\n"
    message += f"Error Code: {result.returncode}\n\n"

        # Deteksi kemungkinan penyebab
        if "choco" in result.stderr.lower() or "chocolatey" in result.stderr.lower():
                message += "🍫 *Kemungkinan Chocolatey belum terinstall di PC target!*\n"
                message += "💡 Solusi:\n1. Jalankan playbook lagi (bot sudah otomatis install Chocolatey di awal)\n"
                message += "2. Pastikan PC online dan terhubung ke internet\n\n"
        else:
                message += "🔧 *Kemungkinan masalah:*\n- Tidak ada koneksi internet\n- Permission issues\n\n"

        message += "💡 *Solusi Umum:*\n1. Jalankan setup_chocolatey.ps1 manual di PC baru\n2. Pastikan koneksi internet\n3. Run sebagai Administrator"

        update.message.reply_text(message, parse_mode="Markdown")

        # Notification
        if result.returncode == 0:
            send_notification(f"✅ INSTALL SUCCESS - {execution_time:.1f}s")
        else:
            send_notification(f"⚠️ INSTALL ISSUES - Code {result.returncode}")

    except subprocess.TimeoutExpired:
        update.message.reply_text("⏰ *Timeout: Proses terlalu lama*\n\nInstalasi Chocolatey butuh waktu lebih lama di PC baru.", parse_mode="Markdown")
        send_notification("INSTALL TIMEOUT")
    except Exception as e:
        update.message.reply_text(f"💥 *Error:* {str(e)}", parse_mode="Markdown")
        send_notification(f"INSTALL ERROR: {str(e)}")

def send_notification(message):
    """Send notification to admin"""
    try:
        bot = Bot(token=TELEGRAM_TOKEN)
        bot.send_message(chat_id=CHAT_ID, text=f"🔔 {message}")
    except Exception as e:
        print(f"Gagal notifikasi: {e}")

def global_error_handler(update, context):
    """Handle semua error yang tidak tertangani"""
    try:
        # Log error
        error_msg = str(context.error) if context.error else "Unknown error"
        print(f"Global Error: {error_msg}")

        # Send user-friendly message
        if update and update.message:
            update.message.reply_text(
                "❌ *Terjadi error sementara*\n\n"
                "💡 *Coba solusi:*\n"
                "• Beberapa PC mungkin offline\n"
                "• Coba lagi dalam 30 detik\n"
                "• Gunakan `/lab_status` untuk cek koneksi\n"
                "• Pastikan network stabil",
                parse_mode="Markdown"
            )
    except Exception as e:
        print(f"Error in error handler: {e}")

def main():
    """Main function"""
    if TELEGRAM_TOKEN == "MASUKKAN_TOKEN_ANDA_DISINI" or not TELEGRAM_TOKEN:
        print("ERROR: Token belum dikonfigurasi!")
        return

    # Validate paths
    required_paths = {
        "Windows Inventory": WINDOWS_INVENTORY_PATH,
        "Software Playbook": WINDOWS_SOFTWARE_PLAYBOOK
    }

    for name, path in required_paths.items():
        if not os.path.exists(path):
            print(f"ERROR: {name} tidak ditemukan: {path}")
            return

    print("✅ Config valid")
    print(f"📁 Project: {PROJECT_PATH}")

    try:
        print("🔗 Testing Telegram connection...")
        bot = Bot(token=TELEGRAM_TOKEN)
        bot_info = bot.get_me()
        print(f"🤖 Bot: {bot_info.first_name} (@{bot_info.username})")

        # Setup updater
        updater = Updater(
            token=TELEGRAM_TOKEN,
            use_context=True,
            request_kwargs={
                'read_timeout': 30,
                'connect_timeout': 30,
            }
        )

        dp = updater.dispatcher

        # Add handlers
        dp.add_handler(CommandHandler("start", start))
        dp.add_handler(CommandHandler("lab_status", lab_status))
        dp.add_handler(CommandHandler("windows_ping", windows_ping))
        dp.add_handler(CommandHandler("install_software", install_software))

        dp.add_error_handler(global_error_handler)

        print("🚀 Bot berjalan...")
        print("📋 Commands: /start, /lab_status, /windows_ping, /install_software")

        updater.start_polling(drop_pending_updates=True)
        updater.idle()

    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()
