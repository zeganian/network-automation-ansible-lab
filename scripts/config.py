# File: scripts/config.py
# ============================
# KONFIGURASI TELEGRAM BOT
# ============================

# Token bot dari @BotFather
TELEGRAM_TOKEN = "8308649279:AAGlCZa_5d5tm05K7TJfQSuP65HWOPFsUyI"  # Ganti dengan token asli

# Chat ID untuk notifikasi
# Cara dapatkan chat ID: jalankan python3 get_chat_id.py
CHAT_ID = "5573513861"  # Ganti dengan chat ID Anda

# ============================
# KONFIGURASI ANSIBLE
# ============================
PROJECT_PATH = "/home/controlnode/network-automation-ansible-lab"
PLAYBOOK_PATH = f"{PROJECT_PATH}/Playbooks/install_nginx.yml"
REMOVE_PLAYBOOK_PATH = f"{PROJECT_PATH}/Playbooks/remove_nginx.yml"
INVENTORY_PATH = f"{PROJECT_PATH}/Inventory/hosts.ini"
