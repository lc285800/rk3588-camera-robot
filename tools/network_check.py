#!/usr/bin/env python3
"""Check the three-computer LAN prerequisites without changing the system."""
import argparse
import socket
import subprocess


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("hosts", nargs="+", help="hostnames/IPs, e.g. robot.local windows.local")
    args = parser.parse_args()
    failed = False
    for host in args.hosts:
        try:
            ip = socket.gethostbyname(host)
            ping = subprocess.run(["ping", "-c", "1", "-W", "2", ip], capture_output=True)
            print(f"{host:24} {ip:16} {'OK' if ping.returncode == 0 else 'NO PING'}")
            failed |= ping.returncode != 0
        except socket.gaierror:
            print(f"{host:24} DNS FAILED")
            failed = True
    raise SystemExit(1 if failed else 0)


if __name__ == "__main__": main()

