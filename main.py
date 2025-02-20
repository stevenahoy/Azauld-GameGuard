import ctypes
import tkinter as tk
from tkinter import Label, Canvas
import time
import hashlib
import psutil
import os
import sys
import threading
import requests
from io import BytesIO
from PIL import Image, ImageTk

# URL API
API_GAMEGUARD = "https://webahoy.org/gameguard/gameguard_api.php"
API_SUBSCRIPTION = "https://webahoy.org/gameguard/subscription_check.php"
API_SPLASH_IMAGE = "https://webahoy.org/gameguard/images/splash.png"

# Fungsi untuk mengecek status langganan
def check_subscription(server_id):
    try:
        response = requests.get(f"{API_SUBSCRIPTION}?server_id={server_id}", timeout=5)
        response.raise_for_status()
        data = response.json()
        return data.get("active", False)
    except requests.RequestException as e:
        print(f"[ERROR] Gagal memeriksa status langganan: {e}")
        return False

# Fungsi untuk mendapatkan daftar hash cheat dari server
def get_cheat_hashes():
    try:
        response = requests.get(API_GAMEGUARD, timeout=5)
        response.raise_for_status()
        data = response.json()
        return data.get("hashes", []), data.get("blacklisted_processes", [])
    except requests.RequestException as e:
        print(f"[ERROR] Gagal mengambil data cheat hashes: {e}")
    return [], []

# Fungsi untuk mengirim log ke server
def send_log_to_server(message):
    try:
        requests.post(API_GAMEGUARD, json={"message": message}, timeout=5)
    except requests.RequestException as e:
        print(f"[ERROR] Gagal mengirim log: {e}")

# Fungsi untuk memeriksa hash dari proses berjalan
def check_running_processes(cheat_hashes, blacklist_hashes, progress_callback):
    detected_cheats = []
    processes = list(psutil.process_iter(attrs=['pid', 'name']))

    for i, process in enumerate(processes):
        try:
            process_name = process.info['name']
            progress_callback(i, len(processes))  # Update loading bar

            if process_name in blacklist_hashes:
                detected_cheats.append(process_name)
                send_log_to_server(f"Blacklisted process detected: {process_name}")
                process.kill()
                continue

            # Cek file hash (jika bisa diakses)
            process_path = process.exe()
            with open(process_path, 'rb') as f:
                file_hash = hashlib.sha256(f.read()).hexdigest()
            
            if file_hash in cheat_hashes:
                detected_cheats.append(process_name)
                send_log_to_server(f"Cheat detected: {process_name}")
                process.kill()
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue

    return detected_cheats

# Fungsi untuk menampilkan splash screen dengan loading bar
def show_splash(server_id):
    splash = tk.Tk()
    splash.overrideredirect(True)

    # Menempatkan splash screen di tengah layar
    screen_width = splash.winfo_screenwidth()
    screen_height = splash.winfo_screenheight()
    window_width, window_height = 400, 250  # Lebar & tinggi
    x_position = (screen_width - window_width) // 2
    y_position = (screen_height - window_height) // 2
    splash.geometry(f"{window_width}x{window_height}+{x_position}+{y_position}")
    
    splash.configure(bg='black')

    frame = tk.Frame(splash, bg='black')
    frame.pack(fill="both", expand=True)

    try:
        response = requests.get(API_SPLASH_IMAGE, timeout=5)
        response.raise_for_status()
        image_data = BytesIO(response.content)
        img = Image.open(image_data)
        img = img.resize((400, 200), Image.LANCZOS)
        splash_image = ImageTk.PhotoImage(img)
        
        label = Label(frame, image=splash_image, bg='black')
        label.image = splash_image
        label.pack(side="top", pady=5)
    except requests.RequestException:
        label = Label(frame, text="Azauld GameGuard", fg="white", bg="black", font=("Arial", 18, "bold"))
        label.pack(side="top", pady=5)
    
    # Loading bar
    canvas = Canvas(frame, width=300, height=10, bg='black', highlightthickness=0)
    canvas.pack(side="bottom", pady=10)
    bar = canvas.create_rectangle(0, 0, 0, 10, fill='green')

    # Fungsi untuk memperbarui loading bar berdasarkan progress scanning
    def update_loading(current, total):
        progress = int((current / total) * 300)
        canvas.coords(bar, 0, 0, progress, 10)
        splash.update()

    # **1. Cek status langganan**
    if not check_subscription(server_id):
        print("[ERROR] Subscription expired! Exiting...")
        sys.exit(1)

    # **2. Ambil daftar cheat hashes**
    cheat_hashes, blacklist_hashes = get_cheat_hashes()

    # **3. Scan proses & update loading bar secara real-time**
    detected_cheats = check_running_processes(cheat_hashes, blacklist_hashes, update_loading)

    # **4. Jika ada cheat, langsung exit**
    if detected_cheats:
        print(f"[DETECTED] Cheat ditemukan: {', '.join(detected_cheats)}")
        sys.exit(1)

    # **5. Tutup splash setelah selesai**
    splash.destroy()

# Fungsi untuk memastikan GameGuard berjalan terus-menerus
def monitor_gameguard(server_id):
    while True:
        if not check_subscription(server_id):
            print("[ERROR] Subscription expired! Exiting...")
            sys.exit(1)

        cheat_hashes, blacklist_hashes = get_cheat_hashes()
        check_running_processes(cheat_hashes, blacklist_hashes, lambda x, y: None)  # Tanpa loading UI

        time.sleep(10)

# Fungsi untuk memulai GameGuard
def start_gameguard(server_id):
    show_splash(server_id)  # **Splash hanya selesai jika scanning sudah benar-benar selesai**
    threading.Thread(target=monitor_gameguard, args=(server_id,), daemon=True).start()

# Fungsi untuk memastikan GameGuard tetap berjalan
def ensure_gameguard_running():
    while True:
        time.sleep(5)
        if not any(proc.name() == "python.exe" for proc in psutil.process_iter()):
            print("[WARNING] GameGuard dihentikan! Memulai ulang...")
            os.execl(sys.executable, sys.executable, *sys.argv)

# Fungsi untuk memulai semuanya
def start(server_id):
    start_gameguard(server_id)
    threading.Thread(target=ensure_gameguard_running, daemon=True).start()
    print("[INFO] GameGuard berjalan dengan sukses!")

if __name__ == "__main__":
    server_id = '1000001'  # Pastikan server_id yang valid
    start(server_id)
