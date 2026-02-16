#!/usr/bin/env python3
"""
Deploy static site to Cloudflare Pages using direct API.
Requires: CLOUDFLARE_API_TOKEN and CLOUDFLARE_ACCOUNT_ID
"""
import os
import sys
import base64
import hashlib
import requests
from pathlib import Path

# Get credentials from environment or wrangler config
def get_wrangler_creds():
    """Extract API token and account ID from wrangler config"""
    home = Path.home()
    config_paths = [
        home / ".config" / "wrangler" / "config.json",
        home / ".wrangler" / "config.json",
    ]

    for config_path in config_paths:
        if config_path.exists():
            import json
            with open(config_path) as f:
                return json.load(f)
    return None

def upload_directory_to_pages(directory, project_name, api_token, account_id):
    """Upload a directory to Cloudflare Pages via direct API"""

    url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/pages/projects/{project_name}/deployments"

    # Collect all files
    files_to_upload = []
    directory = Path(directory)

    for file_path in directory.rglob("*"):
        if file_path.is_file():
            rel_path = file_path.relative_to(directory)
            with open(file_path, "rb") as f:
                content = f.read()
                files_to_upload.append({
                    "path": str(rel_path).replace("\\", "/"),
                    "content": base64.b64encode(content).decode(),
                    "hash": hashlib.sha256(content).hexdigest(),
                    "size": len(content)
                })

    if not files_to_upload:
        print("No files to upload!")
        return False

    # Prepare the deployment payload
    payload = {
        "files": {f["path"]: {"content": f["content"]} for f in files_to_upload}
    }

    headers = {
        "Authorization": f"Bearer {api_token}",
        "Content-Type": "application/json",
    }

    print(f"Uploading {len(files_to_upload)} files to {project_name}...")

    response = requests.post(url, json=payload, headers=headers)

    if response.status_code in (200, 201):
        result = response.json()
        deployment = result.get("result", {})
        url = deployment.get("url", "")
        print(f"Deployment successful!")
        print(f"URL: {url}")
        return url
    else:
        print(f"Deployment failed: {response.status_code}")
        print(response.text)
        return False

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 deploy_pages.py <directory> [project_name]")
        sys.exit(1)

    directory = sys.argv[1]
    project_name = sys.argv[2] if len(sys.argv) > 2 else "badge-generator"

    # Try to get credentials
    creds = get_wrangler_creds()

    if not creds:
        # Try environment variables
        api_token = os.environ.get("CLOUDFLARE_API_TOKEN")
        account_id = os.environ.get("CLOUDFLARE_ACCOUNT_ID")
    else:
        api_token = creds.get("api_token")
        account_id = creds.get("default_account") or creds.get("account_id")

    if not api_token or not account_id:
        print("Error: Could not find Cloudflare credentials")
        print("Set CLOUDFLARE_API_TOKEN and CLOUDFLARE_ACCOUNT_ID environment variables")
        sys.exit(1)

    result = upload_directory_to_pages(directory, project_name, api_token, account_id)

    if result:
        print(f"\nLive at: {result}")
        sys.exit(0)
    else:
        sys.exit(1)

if __name__ == "__main__":
    main()
