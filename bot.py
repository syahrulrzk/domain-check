#!/usr/bin/env python3
"""
Domain Checker + Auto‑Subscribe Telegram Broadcast
==================================================
•  Baca sub‑/domain dari `domain.txt`
•  Cek status HTTP/HTTPS tiap CHECK_INTERVAL
•  Tulis log ke console (warna) & log.csv
•  Siapa pun yang /start bot otomatis di‑subscribe
•  /stop atau /unsubscribe untuk keluar

Cara pakai singkat
------------------
1.  `pip install requests rich colorama`
2.  Export token:
      export TG_TOKEN="57757535423:AAH..."
3.  Jalankan:  `python3 bot.py`
"""

import csv
import json
import os
import re
import sys
import threading
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

import requests
from colorama import Fore, Style, init
from rich import print as rprint

import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
# ────────────────────── Konfigurasi dasar ──────────────────────── #
init(autoreset=True)

CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL", 300))       # detik
TOKEN          = os.getenv("TG_TOKEN")                        # WAJIB ‑ taruh di env var!

BOT_URL    = f"https://api.telegram.org/bot{TOKEN}" if TOKEN else ""
SUB_FILE   = Path("subscribers.json")
DOMAIN_FILE= Path("domain.txt")
LOG_FILE   = Path("log.csv")
TIMEZONE   = timezone(timedelta(hours=7))                      # Asia/Jakarta

# ─────────────────── Utilitas subscriber JSON ──────────────────── #

def _load_subs() -> set[int]:
    if SUB_FILE.exists():
        try:
            return set(json.loads(SUB_FILE.read_text()))
        except json.JSONDecodeError:
            pass
    return set()


def _save_sub(chat_id: int) -> None:
    subs = _load_subs()
    if chat_id not in subs:
        subs.add(chat_id)
        SUB_FILE.write_text(json.dumps(list(subs)))


def _remove_sub(chat_id: int) -> None:
    subs = _load_subs()
    if chat_id in subs:
        subs.remove(chat_id)
        SUB_FILE.write_text(json.dumps(list(subs)))

# ───────────────────────── Telegram utils ──────────────────────── #

def send_telegram(message: str, chat_ids: list[int] | None = None) -> None:
    if not TOKEN:
        return  # Token belum diset

    targets = chat_ids if chat_ids is not None else list(_load_subs())
    if not targets:
        return

    for cid in targets:
        try:
            resp = requests.post(
                f"{BOT_URL}/sendMessage",
                json={
                    "chat_id": cid,
                    "text": message,
                    "parse_mode": "Markdown",
                    "disable_web_page_preview": True,
                },
                timeout=5,
            )
            resp.raise_for_status()
        except Exception as e:
            rprint(f"[yellow][⚠ Telegram Error to {cid}] {e}[/]")


# ───────────────────── Polling /start‑/stop thread ─────────────── #

def poll_updates():
    if not TOKEN:
        return
    offset = 0
    while True:
        try:
            resp = requests.get(
                f"{BOT_URL}/getUpdates",
                params={"timeout": 30, "offset": offset},
                timeout=35,
            ).json()
            for upd in resp.get("result", []):
                offset = upd["update_id"] + 1
                msg = upd.get("message") or upd.get("edited_message")
                if not msg:
                    continue
                cid  = msg["chat"]["id"]
                text = (msg.get("text") or "").lower()

                if text in {"/start", "/subscribe"}:
                    _save_sub(cid)
                    send_telegram("✅ Kamu sudah *subscribe* ke alert domain.", [cid])
                elif text in {"/stop", "/unsubscribe"}:
                    _remove_sub(cid)
                    send_telegram("❎ Kamu sudah *unsubscribe*. Bye!", [cid])
        except Exception as e:
            rprint(f"[yellow][Polling error] {e}[/]")
            time.sleep(5)
        time.sleep(1)

# ──────────────────────── Log & warna utils ────────────────────── #

ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


def strip_ansi(text: str) -> str:
    return ANSI_RE.sub("", text)


def log_to_csv(status: str, url: str, info: str | int):
    is_new = not LOG_FILE.exists()
    with LOG_FILE.open("a", newline="") as f:
        w = csv.writer(f)
        if is_new:
            w.writerow(["Timestamp", "Status", "URL", "Response"])
        w.writerow([datetime.now(TIMEZONE).isoformat(), status, url, info])


def get_status_desc(code: int) -> str:
    mapping = {
        200: "OK", 201: "Created", 202: "Accepted", 204: "No Content",
        301: "Moved Permanently", 302: "Found", 400: "Bad Request",
        401: "Unauthorized", 403: "Forbidden", 404: "Not Found",
        405: "Method Not Allowed", 408: "Request Timeout", 500: "Internal Server Error",
        502: "Bad Gateway", 503: "Service Unavailable", 504: "Gateway Timeout",
    }
    return mapping.get(code, "Unknown")


def print_colored(status: str, url: str, info: str | int, idx: int):
    if status == "OK":
        color, icon = Fore.GREEN, "✅"
    elif status == "ERROR":
        color, icon = Fore.YELLOW, "⚠"
    else:
        color, icon = Fore.RED, "❌"

    try:
        width = os.get_terminal_size().columns
    except OSError:
        width = 120

    url_line = f"{Style.BRIGHT}{idx}. Website -> {url}{Style.RESET_ALL}"

    if isinstance(info, int):
        desc = get_status_desc(info)
        right = f"------> {status.ljust(7)} Status : {info} {desc} {icon}"
    else:
        right = f"------> {status.ljust(7)} Status : {info[:60]} {icon}"

    print("─" * width)
    print(url_line)
    print(f"{color}{right.rjust(width)}")

# ─────────────────────── Checker fungsi utama ──────────────────── #

def read_domains() -> list[str]:
    if not DOMAIN_FILE.exists():
        rprint(f"[red]File {DOMAIN_FILE} tidak ditemukan![/]")
        return []
    return [l.strip() for l in DOMAIN_FILE.read_text().splitlines() if l.strip()]


def check_site(domain: str, idx: int):
    urls = [f"https://{domain}", f"http://{domain}"]
    print(f"🔄 Checking ({idx}) -> {urls[0]}", end="\r")
    last_error: str | int = "Unknown error"

    for url in urls:
        try:
            response = requests.get(url, timeout=5, verify=False)
            sc = response.status_code
            if 200 <= sc < 300:
                log_to_csv("OK", url, sc)
                return "OK", url, sc
            else:
                log_to_csv("ERROR", url, sc)
                return "ERROR", url, sc
        except requests.exceptions.SSLError:
            continue  # coba http berikutnya
        except requests.exceptions.RequestException as e:
            last_error = str(e)
            continue

    # jika kedua percobaan gagal
    log_to_csv("DOWN", f"https://{domain}", last_error)
    send_telegram(f"❌ *{domain}* DOWN!\nReason: {last_error}")
    return "DOWN", f"https://{domain}", last_error

# ─────────────────────────── Banner ────────────────────────────── #

def banner():
    try:
        width = os.get_terminal_size().columns
    except OSError:
        width = 120

    print("═" * width)
    print(f"{Style.BRIGHT}{Fore.CYAN}{'CEK DOMAIN SIM'.center(width)}{Style.RESET_ALL}")
    print("═" * width)
    print(f"{Fore.GREEN} ✅ 200: OK")
    print(f"{Fore.YELLOW} ⚠ 404: Not Found / 405: Method Not Allowed")
    print(f"{Fore.RED} ❌ 502/504: Gateway Timeout / DOWN (SSL/Timeout)")
    print("═" * width)

# ─────────────────────────── Main loop ─────────────────────────── #

def main():
    banner()
    domains = read_domains()
    if not domains:
        return

    while True:
        now = datetime.now(TIMEZONE).strftime("%Y-%m-%d %H:%M:%S")
        rprint(f"\n[bold]🔍 Checking subdomain status... ({now})[/]")

        total = len(domains)
        for i, domain in enumerate(domains, 1):
            pct = int(i / total * 100)
            sys.stdout.write(f"\r🔄 Progress {pct}% - {domain}...")
            sys.stdout.flush()

            status, url, info = check_site(domain, i)
            sys.stdout.write(" " * 80 + "\r")
            print_colored(status, url, info, i)
            time.sleep(0.2)

        rprint(f"\n[green]✅ Done. Next check in {CHECK_INTERVAL} s.[/]")
        time.sleep(CHECK_INTERVAL)

# ──────────────────────────── Entrypoint ───────────────────────── #

if __name__ == "__main__":
    if not TOKEN:
        rprint("[red]>> Set TG_TOKEN environment variable dulu![/]")
        sys.exit(1)

    # Start polling thread
    threading.Thread(target=poll_updates, daemon=True).start()

    try:
        main()
    except KeyboardInterrupt:
        rprint("\n[yellow]Bye![/]")
