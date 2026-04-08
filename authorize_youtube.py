#!/usr/bin/env python3
"""
One-time YouTube OAuth Authorization Script (Desktop App version).

Run this ONCE to authorize your Google account.
It will create youtube_token.json for automatic uploads.
"""

import os
import sys

# Add project root to path (optional, depending on your setup)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

print("=" * 60)
print("YouTube OAuth Authorization (Desktop App)")
print("=" * 60)
print()

# Check if client_secrets.json exists
if not os.path.exists("client_secrets.json"):
    print("❌ ERROR: client_secrets.json not found!")
    print()
    print("Please download it from Google Cloud Console:")
    print("1. Go to https://console.cloud.google.com/apis/credentials")
    print("2. Create OAuth 2.0 Client ID → Desktop App")
    print("3. Download JSON and save as 'client_secrets.json' in project root")
    sys.exit(1)

print("✓ client_secrets.json found")
print()

# Check if already authorized
if os.path.exists("youtube_token.json"):
    print("⚠ Already authorized!")
    response = input("Do you want to re-authorize? (y/N): ")
    if response.lower() != 'y':
        print("Exiting...")
        sys.exit(0)
    print("Removing old token...")
    os.remove("youtube_token.json")

print()
print("INSTRUCTIONS:")
print("1. A URL will be displayed in the terminal")
print("2. Open it in your browser and sign in with your Google account")
print("3. Click 'Allow' to grant permissions")
print("4. Copy the code displayed and paste it back here")
print("5. This script will save the token automatically")
print()
input("Press Enter to continue...")

try:
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from google_auth_oauthlib.flow import InstalledAppFlow

    SCOPES = [
        "https://www.googleapis.com/auth/youtube.upload",
        "https://www.googleapis.com/auth/youtube",
        "https://www.googleapis.com/auth/youtube.force-ssl",
    ]

    # Use Desktop App flow (no redirect URI required)
    flow = InstalledAppFlow.from_client_secrets_file(
        "client_secrets.json",
        SCOPES
    )

    # Run console-based authorization
    creds = flow.run_local_server(port=0)  # port=0 → auto free port

    # Save token for future use
    with open("youtube_token.json", "w") as f:
        f.write(creds.to_json())

    print()
    print("=" * 60)
    print("✅ SUCCESS! Authorization complete!")
    print("=" * 60)
    print(f"Token saved to: youtube_token.json")
    print()
    print("You can now upload videos to YouTube automatically!")

except Exception as e:
    print()
    print("=" * 60)
    print(f"❌ ERROR: {e}")
    print("=" * 60)
    print()
    print("Troubleshooting:")
    print("1. Make sure client_secrets.json is valid")
    print("2. Ensure your Google account allows OAuth")
    sys.exit(1)