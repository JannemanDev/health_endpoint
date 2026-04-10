#!/bin/bash
set -x  # Show commands as they are executed

cd /volume1/Apps/health_endpoint
/usr/bin/python3 ip_change.py ip_change-home-settings.json
