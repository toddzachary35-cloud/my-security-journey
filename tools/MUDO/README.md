# MUDO — Open Security Toolkit

**MUDO** is a menu-driven, terminal-based security toolkit for Linux. It wraps a
wide range of well-known offensive-security and OSINT tools behind a single,
themed command-center so you can run scans, reconnaissance, and analysis from one
place without memorizing every flag.

This is the **open / multi-user edition**: it starts straight into the toolkit —
no login, no password. Each user who runs it gets their own private notes and
logs automatically (stored in their own home directory).

Built for **learning, CTFs, home labs, and authorized penetration testing.**

---

## ⚠️ Legal & ethical use — read this first

MUDO only orchestrates tools that are already installed on your system, and many
of them are powerful.

> **Only use MUDO against systems you own or have explicit, written permission to
> test.** Unauthorized scanning, credential attacks, phishing, or exploitation is
> illegal in most countries. You alone are responsible for how you use it.

The **"DDoS"** option is a harmless on-screen animation — it sends no traffic.
The social-engineering entries are educational templates and launchers for tools
you must install yourself.

---

## Features

MUDO is split into a **Red Team** section and a **Tools** section.

### Red Team
| Category | Tools |
|---|---|
| **Web Hacking** | Gobuster, Nikto, Netcat, SQLMap |
| **Network Hacking** | Packet capture (tshark/tcpdump), Nmap (quick / TCP / SYN / version / full), Hydra, ARP scan |
| **Social Engineering** | Zphisher, SET phishing kit, pretexting template, fake login page, USB-drop guide |
| **Password Attacks** | Hydra, John the Ripper, Hashcat, hash identifier |
| **OSINT** | WHOIS, reverse IP, domain reputation, Sherlock, theHarvester, Have I Been Pwned |
| **Malware** | msfvenom payload generator, static file analyser, VirusTotal hash checker, suspicious-process detector, string extractor, Searchsploit, malware notes |
| **Exploitation** | Metasploit / msfvenom / Searchsploit launch points |

### Tools
| Feature | What it does |
|---|---|
| **Black Hat** | proxychains config, Tor launcher, (fake) DDoS, leave-network, MAC spoofing, FSociety screen, Hacker News feed |
| **Notes** | save / view / delete target notes + a password-protected hidden-notes vault |
| **Network Diagnostics** | OS / CPU / memory / IP info and a live network-speed meter |
| **Tool Checker** | reports which supported tools are installed and how to install the rest |
| **Report Generator** | dumps your session log and notes to a timestamped report |
| **VPN Checker** | shows your public IP and looks for running VPN processes |
| **Session Log Viewer** | view the tool-usage log |

A live status header shows your IP, MAC, and proxy/Tor state throughout.

---

## Requirements

- **Linux** (developed/tested on Debian/Ubuntu/Kali/Mint-style systems)
- **Python 3.8+** — standard library only, **no `pip` dependencies**
- The external tools you actually plan to use (nmap, sqlmap, hydra, gobuster,
  tshark/tcpdump, whois, dig, macchanger, etc.)

MUDO degrades gracefully: if a tool isn't installed, it tells you and prints the
install command instead of crashing. Run the **Tool Checker** from the menu
(option 11) to see your current coverage at any time.

---

## Installation

```bash
# 1. Clone the repository
git clone https://github.com/toddzachary35-cloud/My-security-journey-.git

# 2. Go to the tool
cd My-security-journey-/tools/MUDO

# 3. Run it
python3 mudo.py
```

### Optional: run it as a command

Make it executable and link it onto your PATH so you can run `mudo` from anywhere:

```bash
chmod +x mudo.py
sudo ln -s "$(pwd)/mudo.py" /usr/local/bin/mudo
mudo
```

### Elevated privileges

Some actions need root (packet capture, MAC spoofing, taking an interface down,
SYN scans). For those, run:

```bash
sudo python3 mudo.py
```

---

## Usage

Launch it and follow the numbered menus:

```bash
python3 mudo.py
```

You'll see the banner, then go straight to the main menu. Pick a category by
number, drill into a tool, and MUDO builds and runs the command for you.

### Configuration (optional API keys)

Two features call external APIs. Set these environment variables before launching
if you want them:

| Variable | Used by | Get a key |
|---|---|---|
| `HIBP_API_KEY` | Have I Been Pwned | https://haveibeenpwned.com/API/Key |
| `VT_API_KEY` / `VIRUSTOTAL_API_KEY` | VirusTotal hash checker | https://www.virustotal.com/ |

```bash
export HIBP_API_KEY="your-key-here"
export VT_API_KEY="your-key-here"
python3 mudo.py
```

### Multi-user & data files

MUDO is multi-user friendly: there's no shared login, and every file it creates
lives in the **current user's** home directory, so users never see each other's
data.

- `~/.mudo_log.txt` — session tool-usage log
- `~/.mudo_notes.txt` — saved target notes
- `~/.mudo_hidden_notes.txt` — hidden-vault notes
- `~/.mudo_malware_notes.txt` — malware notes
- `~/.mudo_vault_hash` — the hidden vault's password hash (per user)
- `~/MUDO_report_<timestamp>.txt` — generated reports

**Hidden-notes vault:** the first time a user opens it, they set their own
password; it's stored only as a SHA-256 hash in `~/.mudo_vault_hash` (file
permissions `600`). There is no default or master password.

---

## License

This tool is distributed under the license of the parent repository. See the
[LICENSE](../../LICENSE) file in the repo root.
