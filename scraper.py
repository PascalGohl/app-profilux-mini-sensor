#!/usr/bin/env python3
"""Dev/debug CLI — reads ProfiLux sensors and prints JSON to stdout.

Usage:
  PROFILUX_HOST=10.1.1.178 PROFILUX_USER=admin PROFILUX_PASSWORD=secret python3 scraper.py
"""
import json
import os
import sys

from sensor import fetch_readings

if __name__ == "__main__":
    host     = os.environ.get("PROFILUX_HOST", "10.1.1.178")
    user     = os.environ.get("PROFILUX_USER", "admin")
    password = os.environ.get("PROFILUX_PASSWORD", "Starfish")

    try:
        print(json.dumps(fetch_readings(host, user, password)))
    except Exception as exc:
        print(json.dumps({"temperature": None, "ph": None, "error": str(exc)}))
        sys.exit(1)
