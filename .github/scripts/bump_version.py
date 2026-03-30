#!/usr/bin/env python3
"""Helper script to bump patch version in pyproject.toml"""

import os
import re
import sys
from pathlib import Path

pyproject = Path("pyproject.toml")
content = pyproject.read_text(encoding="utf-8")

match = re.search(r'version\s*=\s*"(\d+)\.(\d+)\.(\d+)"', content)
if not match:
    print("ERROR: Could not find semantic version in pyproject.toml", file=sys.stderr)
    sys.exit(1)

major, minor, patch = map(int, match.groups())
old_version = f"{major}.{minor}.{patch}"
new_version = f"{major}.{minor}.{patch + 1}"

# Update pyproject.toml
updated = re.sub(
    r'version\s*=\s*"\d+\.\d+\.\d+"',
    f'version = "{new_version}"',
    content,
    count=1,
)
pyproject.write_text(updated, encoding="utf-8")

# Output for GitHub Actions
github_output = Path(os.environ.get("GITHUB_OUTPUT", "/tmp/github_output"))
with open(github_output, "a", encoding="utf-8") as out:
    out.write(f"old_version={old_version}\n")
    out.write(f"new_version={new_version}\n")

print(f"Version bumped: {old_version} -> {new_version}")
