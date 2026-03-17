<div align="center">
  <img src="images/gitbackup.png" alt="gitbackup" width="120"/>
  <h1>gh-backup</h1>
  <p>A command-line tool to enumerate and back up all your GitHub repositories using the GitHub API.<br>Supports owned and forked repositories, HTTPS and SSH cloning, and idempotent incremental updates.</p>
</div>

---

## Features

- Enumerates all repositories associated with your account (owned, forked, collaborator, organization)
- Displays a sorted summary table with repository size, visibility, fork status, and last updated timestamp
- Clones repositories to a local directory for offline backup
- Skips already-cloned repositories and performs `git pull` to update them instead
- Gracefully skips repositories that are inaccessible due to authentication errors, ToS violations, or other issues
- Supports both HTTPS (token-based) and SSH authentication
- Handles GitHub API pagination transparently for accounts with large numbers of repositories

---

## Requirements

- Python 3.10 or higher
- `git` installed and available in your `PATH`
- A GitHub Personal Access Token (PAT)

Install the Python dependency:

```bash
pip install requests
```

---

## Authentication

### Recommended: Fine-Grained Personal Access Token

Create a Fine-Grained PAT at **GitHub > Settings > Developer settings > Personal access tokens > Fine-grained tokens** with the following permissions:

| Permission | Level |
|---|---|
| Metadata | Read-only |
| Contents | Read-only |

This ensures the token is cryptographically incapable of modifying, deleting, or changing the visibility of any repository.

### Alternative: Classic Personal Access Token

If your tooling requires a Classic PAT, use the following scopes:

| Scope | Purpose |
|---|---|
| `public_repo` | Access public repositories |
| `repo` (full) | Access private repositories |
| `read:user` | Read authenticated user profile |

> Classic PATs grant write access as a side effect of `repo` scope. Fine-Grained tokens are strongly preferred.

---

## Usage

Export your token as an environment variable (recommended to avoid shell history exposure):

```bash
export GITHUB_TOKEN="your_token_here"
```

### Enumerate repositories only

```bash
python gh_backup.py
```

### Enumerate and clone via HTTPS

```bash
python gh_backup.py --clone --dest ~/backups/github
```

### Enumerate and clone via SSH

```bash
python gh_backup.py --clone --ssh --dest ~/backups/github
```

### Clone owned repositories only, skip forks

```bash
python gh_backup.py --clone --no-forks --owned-only --dest ~/backups/github
```

---

## Options

| Flag | Description |
|---|---|
| `--token`, `-t` | GitHub PAT. Defaults to `GITHUB_TOKEN` environment variable |
| `--clone`, `-c` | Clone or update repositories after enumeration |
| `--dest`, `-d` | Destination directory for cloned repositories. Default: `./github_backup` |
| `--ssh` | Use SSH URLs instead of HTTPS for cloning |
| `--no-forks` | Exclude forked repositories from cloning |
| `--owned-only` | Only include repositories owned by the authenticated user |

---

## Output Example

```
[*] Authenticated as : 0xsyr0 (syr0)
[*] Public repos     : 42
[*] Private repos    : 7
[*] Fetching repository list...

Repository                                         Fork   Private  Size       Last Updated
-------------------------------------------------------------------------------------------
0xsyr0/Awesome-Cybersecurity-Handbooks             no     no       18.23 MB   2024-11-03 14:22
0xsyr0/mimikatz                                    yes    no       9.10 MB    2024-09-18 08:45
...
-------------------------------------------------------------------------------------------
  Total: 49 repositories — 97.41 MB

[*] Cloning 49 repositories to: ./github_backup

  [+] Cloning   : 0xsyr0/Awesome-Cybersecurity-Handbooks  (18.23 MB)
  [~] Updating  : 0xsyr0/mimikatz
  [!] Skipping  : 0xsyr0/SomeRepo
      Reason    : fatal: repository not found

[*] Done — 48/49 succeeded.
[!] Skipped (1):
    - 0xsyr0/SomeRepo
```

---

## Safety

This tool is strictly read-only with respect to your GitHub account.

Every GitHub API call issued by this tool uses the HTTP `GET` method. No `POST`, `PATCH`, `PUT`, or `DELETE` requests are made at any point. `git clone` and `git pull` only write to your local filesystem and have no write-back capability to any remote.

You can verify this independently:

```bash
grep -iE "(POST|PATCH|PUT|DELETE|push|delete|visibility)" gh_backup.py
```

---

## License

MIT
