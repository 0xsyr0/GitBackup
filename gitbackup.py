#!/usr/bin/env python3

"""
GitHub Repository Enumerator & Backup Tool
Enumerates all repos (woned + forked) and optionally clones them.
"""

import os
import sys
import argparse
import subprocess
import requests
from typing import Optional

# ── Config ─────────────────────────────────────────────────────────────────────
GITHUB_API = "https://api.github.com"
PER_PAGE   = 100 # max allowed by GitHub API

def get_headers(token: str) -> dict:
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

# ── Fetch all repos (handles pagination) ───────────────────────────────────────
def fetch_all_repos(token: str) -> list[dict]:
    repos = []
    page = 1

    while True:
        resp = requests.get(
            f"{GITHUB_API}/user/repos",
            headers=get_headers(token),
            params={
                "visibility":  "all", # public + private
                "affiliation": "owner,collaborator,organization_member",
                "per_page":    PER_PAGE,
                "page":        page,
            },
            timeout=15,
        )
        resp.raise_for_status()
        batch = resp.json()

        if not batch:
            break

        repos.extend(batch)
        page += 1

    return repos

# ── Formatting helpers ──────────────────────────────────────────────────────────
def fmt_size(kb: int) -> str:
    """GitHub reports size in KB."""
    if kb < 1024:
        return f"{kb} KB"
    elif kb < 1024 ** 2:
        return f"{kb / 1024:.2f} MB"
    else:
        return f"{kb / 1024 ** 2:.2f} GB"

def print_repo_table(repos: list[dict]) -> int:
    """Prints a summary table. Return total size in KB."""
    col = {
        "name":    50,
        "fork":     6,
        "private":  8,
        "size":    10,
        "updated": 22,
    }

    header = (
        f"{'Repository':<{col['name']}} "
        f"{'Fork':<{col['fork']}} "
        f"{'Private':<{col['size']}} "
        f"{'Size':<{col['size']}} "
        f"{'Last Updated':<{col['updated']}}"
    )
    print("\n" + header)
    print("-" * len(header))

    total_kb = 0
    for r in sorted(repos, key=lambda x: x["size"], reverse=True):
        name     = r["full_name"][:col["name"]]
        fork     = "yes" if r["fork"] else "no"
        private  = "yes" if r["private"] else "no"
        size     = fmt_size(r["size"])
        updated  = r["updated_at"][:19].replace("T", " ")
        total_kb += r["size"]

        print("-" * len(header))
        print(f"  Total: {len(repos)} repositories - {fmt_size(total_kb)}\n")
        return total_kb

# ── Clone / update repos ────────────────────────────────────────────────────────
def clone_or_pull(repo: dict, dest: str, token: str, use_ssh: bool) -> int:
    name     = repo["full_name"]
    repo_dir = os.path.join(dest, name.replace("/", "_"))

    if use_ssh:
        url = repo["ssh_url"]
    else:
        from urllib.parse import quote
        encoded_token = quote(token, safe="")
        url = repo["clone_url"].replace("https://", f"https://{encoded_token}@")

    env = os.environ.copy()
    env["GIT_TERMINAL_PROMPT"] = "0"

    if os.path.isdir(os.path.join(repo_dir, ".git")):
        print(f"[~] Updating : {name}")
        result = subprocess.run(["git", "-C", repo_dir, "pull", "--quiet"], env=env, capture_output=True, text=True)
    else:
        print(f"[+] Cloning : {name} ({fmt_size(repo['size'])})")
        os.makedirs(repo_dir, exist_ok=True)
        result = subprocess.run(["git", "clone", "--quiet", url, repo_dir], env=env, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"  [!] Skipping  : {name}")
        print(f"      Reason    : {result.stderr.strip().splitlines()[-1]}")
        return result.returncode

    return 0

def clone_repos(repos: list[dict], dest: str, token: str, use_ssh: bool, include_forks: bool) -> None:
    targets = repos if include_forks else [r for r in repos if not r["fork"]]
    print(f"\n[*] Cloning {len(targets)} repositories to: {dest}\n")
    os.makedirs(dest, exist_ok=True)

    skipped = []
    for repo in targets:
        rc = clone_or_pull(repo, dest, token, use_ssh)
        if rc != 0:
            skipped.append(repo["full_name"])

    print(f"\n[*] Done — {len(targets) - len(skipped)}/{len(targets)} succeeded.")
    if skipped:
        print(f"[!] Skipped ({len(skipped)}):")
        for name in skipped:
            print(f" - {name}")

# ── Auth check ──────────────────────────────────────────────────────────────────
def verify_token(token: str) -> dict:
    resp = requests.get(f"{GITHUB_API}/user", headers=get_headers(token), timeout=10)
    if resp.status_code == 401:
        print("[!] Invalid or expired token.")
        sys.exit(1)
    resp.raise_for_status()
    return resp.json()

# ── CLI ─────────────────────────────────────────────────────────────────────────
def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Enumerate and optionally back up all your GitHub resposiories."
    )
    p.add_argument(
        "--token", "-t",
        default=os.environ.get("GITHUB_TOKEN"),
        help="GitHub PAT (or set GITHUB_TOKEN env var)",
    )
    p.add_argument(
        "--clone", "-c",
        action="store_true",
        help="Clone / update repositories after enumeration",
    )
    p.add_argument(
        "--dest", "-d",
        default="./github_backup",
        help="Destination directory for cloned repos (default: ./github_backup)",
    )
    p.add_argument(
        "--ssh",
        action="store_true",
        help="Use SSH URLs instead of HTTPS for cloning",
    )
    p.add_argument(
        "--no-forks",
        action="store_true",
        help="Exclude forked repositories from cloning",
    )
    p.add_argument(
        "--owned-only",
        action="store_true",
        help="Only list/clone repos you own (exclude collaborator/org repos)",
    )
    return p.parse_args()

def main()-> None:
    args = parse_args()

    if not args.token:
        print("[!] No token provided. Use --token or set GITHUB_TOKEN.")
        sys.exit(1)

    user = verify_token(args.token)
    print(f"[*] Authenticated as : {user['login']} ({user.get('name', 'N/A')})")
    print(f"[*] Public repos     : {user['public_repos']}")
    print(f"[*] Private repos    : {user.get('total_private_repos', 'N/A')}")

    print (f"[*] Fetching repository list...")
    repos = fetch_all_repos(args.token)

    if args.owned_only:
        repos = [r for r in repos if r["owner"]["login"] == user["login"]]

    print_repo_table(repos)

    if args.clone:
        clone_repos(
            repos,
            dest=args.dest,
            token=args.token,
            use_ssh=args.ssh,
            include_forks=not args.no_forks,
        )
    else:
        print("[i] Run with --clone to back up repositories.\n")

if __name__ == "__main__":
    main()