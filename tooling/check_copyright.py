#!/usr/bin/env python3

# Copyright © Advanced Micro Devices, Inc., or its affiliates.
#
# SPDX-License-Identifier: MIT


import argparse
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

# File extensions to exclude from copyright check
EXCLUDED_EXTENSIONS = {
    ".bin",
    ".cache",
    ".csv",
    ".doc",
    ".docx",
    ".gif",
    ".gz",
    ".ico",
    ".jpeg",
    ".jpg",
    ".json",
    ".log",
    ".map",
    ".mjs",
    ".mod",
    ".pdf",
    ".png",
    ".sum",
    ".svg",
    ".tar",
    ".tmp",
    ".tsv",
    ".webp",
    ".xml",
    ".zip",
    ".patch",
}

EXCLUDED_FILES = {"pnpm-lock.yaml", "uv.lock", "LICENSE"}

EXCLUDED_DIRS = {".git"}

# Comment styles grouped by type
COMMENT_STYLES_GROUPS = {
    # Hash/pound comments
    ("# ", ""): [
        ".bash",
        ".cfg",
        ".dockerfile",
        ".dockerignore",
        ".env",
        ".fish",
        ".flake8",
        ".gitattributes",
        ".gitignore",
        ".ini",
        ".jinja",
        ".jsonl",
        ".lock",
        ".mdc",
        ".prettierignore",
        ".prettierrc",
        ".puml",
        ".py",
        ".resource",
        ".robot",
        ".sh",
        ".shellcheckrc",
        ".toml",
        ".txt",
        ".yaml",
        ".yml",
        ".zsh",
        "dockerfile",
    ],
    # Double slash comments
    ("// ", ""): [
        ".js",
        ".ts",
        ".tsx",
        ".jsx",
    ],
    # HTML/XML style comments
    ("<!--\n", "\n-->"): [".html", ".htm", ".md", ".markdown"],
    # CSS style comments
    ("/*\n", "\n*/"): [".css", ".scss", ".sass", ".less"],
    # SQL comments
    ("-- ", ""): [".sql"],
}

# Default comment style for unknown file types
DEFAULT_COMMENT_STYLE = ("# ", "")

COPYRIGHT_PATTERNS = [
    re.compile(
        r"Copyright\s*©\s*Advanced\s+Micro\s+Devices,\s*Inc\.,\s*or\s+its\s+affiliates\.",
        re.MULTILINE | re.IGNORECASE,
    ),
    re.compile(
        r"Copyright\s*\(c\)\s*Advanced\s+Micro\s+Devices,\s*Inc\.,\s*or\s+its\s+affiliates\.",
        re.MULTILINE | re.IGNORECASE,
    ),
    re.compile(
        r"SPDX-License-Identifier:\s*MIT",
        re.MULTILINE | re.IGNORECASE,
    ),
]

COPYRIGHT_TEXT = "Copyright © Advanced Micro Devices, Inc., or its affiliates.\n\nSPDX-License-Identifier: MIT"


def find_git_root():
    git_root = Path.cwd()
    while git_root != git_root.parent and not (git_root / ".git").exists():
        git_root = git_root.parent
    return git_root


git_root = find_git_root()

# Cache for git ignore status to avoid repeated git calls
_gitignore_cache: dict = {}


def populate_gitignore_cache(file_paths):
    """
    Populate the gitignore cache for multiple files using a single git check-ignore --stdin command.
    Updates the _gitignore_cache dictionary with ignore status for all provided file paths.
    """
    if not file_paths:
        return set()

    # Convert all paths to relative paths from git root
    relative_paths = []
    path_mapping = {}  # Map relative path back to original Path object

    for file_path in file_paths:
        if str(file_path) in _gitignore_cache:
            continue

        try:
            if not file_path.is_absolute():
                file_path = git_root / file_path
            relative_path = file_path.relative_to(git_root)
            relative_paths.append(str(relative_path))
            path_mapping[str(relative_path)] = file_path
        except ValueError:
            # File is outside git repository
            _gitignore_cache[str(file_path)] = False

    if not relative_paths:
        return set()

    ignored_files = set()

    try:
        # Use git check-ignore --stdin for batch processing
        input_text = "\n".join(relative_paths) + "\n"
        result = subprocess.run(
            ["git", "check-ignore", "--stdin"],
            cwd=git_root,
            input=input_text,
            capture_output=True,
            text=True,
            timeout=10,  # Prevent hanging
        )

        # Parse the output - git check-ignore returns the paths that are ignored
        if result.stdout:
            for ignored_path in result.stdout.strip().split("\n"):
                if ignored_path and ignored_path in path_mapping:
                    original_path = path_mapping[ignored_path]
                    ignored_files.add(original_path)
                    _gitignore_cache[str(original_path)] = True

        # Cache non-ignored files
        for rel_path, original_path in path_mapping.items():
            if original_path not in ignored_files:
                _gitignore_cache[str(original_path)] = False

    except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError):
        # Git command failed or git is not available, assume not ignored
        for original_path in path_mapping.values():
            _gitignore_cache[str(original_path)] = False


def is_gitignored(file_path):
    """
    Check if a file is ignored by git. Uses cached results from batch_check_gitignored.
    """
    return _gitignore_cache.get(str(file_path), False)


def has_copyright(file_path):
    try:
        with open(file_path, encoding="utf-8", errors="ignore") as f:
            content = f.read(1000)
        has_copyright_line = COPYRIGHT_PATTERNS[0].search(content) or COPYRIGHT_PATTERNS[1].search(content)
        has_license_line = COPYRIGHT_PATTERNS[2].search(content)
        return bool(has_copyright_line and has_license_line)
    except Exception:
        return False


def check_single_file(file_path):
    """Check a single file for copyright compliance."""
    if (
        not is_gitignored(file_path)
        and not any(part in EXCLUDED_DIRS for part in file_path.parts)
        and file_path.is_file()
        and file_path.suffix not in EXCLUDED_EXTENSIONS
        and file_path.name not in EXCLUDED_FILES
        and get_comment_style(file_path)  # Only check files that support comments
        and not has_copyright(file_path)
    ):
        return file_path
    return None


def check_files(file_paths):
    missing = []

    if not file_paths:
        return missing

    # Populate git ignore cache for all files first
    populate_gitignore_cache(file_paths)

    max_workers = min(32, len(file_paths))

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_file = {executor.submit(check_single_file, file_path): file_path for file_path in file_paths}

        for future in as_completed(future_to_file):
            result = future.result()
            if result is not None:
                missing.append(result)

    return missing


def get_comment_style(file_path):
    suffix = file_path.suffix.lower()
    name = file_path.name.lower()

    # Search through comment style groups
    for (comment_start, comment_end), extensions in COMMENT_STYLES_GROUPS.items():
        if suffix in extensions or name in extensions:
            return (comment_start, comment_end)

    # Use default comment style with warning
    print(
        f"⚠️  Warning: Unknown file type '{file_path}', using default hash comments. Consider adding to COMMENT_STYLES_GROUPS."
    )
    return DEFAULT_COMMENT_STYLE


def create_copyright_header(comment_start, comment_end):
    if comment_end:  # Multi-line comment style
        return f"{comment_start}{COPYRIGHT_TEXT}{comment_end}\n"
    else:  # Single-line comment style
        lines = COPYRIGHT_TEXT.split("\n")
        header_lines = []
        for line in lines:
            if line.strip():
                header_lines.append(f"{comment_start}{line}")
            else:
                header_lines.append(comment_start.rstrip())
        return "\n".join(header_lines) + "\n"


def add_copyright_to_file(file_path):
    comment_style = get_comment_style(file_path)
    if not comment_style:
        return False
    comment_start, comment_end = comment_style

    try:
        with open(file_path, encoding="utf-8") as f:
            content = f.read()

        copyright_header = create_copyright_header(comment_start, comment_end)

        # Handle shebang lines
        if content.startswith("#!"):
            lines = content.split("\n", 1)
            if len(lines) > 1:
                new_content = lines[0] + "\n\n" + copyright_header + lines[1]
            else:
                new_content = lines[0] + "\n\n" + copyright_header
        else:
            if content.strip():
                new_content = copyright_header + "\n" + content
            else:
                new_content = copyright_header

        # Ensure file ends with newline
        if not new_content.endswith("\n"):
            new_content += "\n"

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(new_content)

        return True
    except Exception:
        return False


def add_copyright_to_files(files):
    success_count = 0
    for file_path in files:
        if add_copyright_to_file(file_path):
            success_count += 1
            print(f"✅ Added copyright to {file_path}")
        else:
            print(f"❌ Failed to add copyright to {file_path}")

    return success_count


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Check for AMD copyright boilerplate")
    parser.add_argument("--fix", action="store_true", help="Automatically add missing copyright headers")
    parser.add_argument("files", nargs="*", help="Files to check (if not provided, checks all files)")

    args = parser.parse_args()

    if args.files:
        files = [Path(f) for f in args.files]
    else:
        files = list(Path.cwd().rglob("*"))
        if not args.fix:
            print("Checking for AMD copyright boilerplate...")

    missing = check_files(files)

    if missing:
        if args.fix:
            print(f"Adding copyright headers to {len(missing)} files...")
            success_count = add_copyright_to_files(missing)
            print(f"\n✅ Successfully added copyright headers to {success_count}/{len(missing)} files!")
            sys.exit(0 if success_count == len(missing) else 1)
        else:
            print(f"\n❌ Found {len(missing)} files without AMD copyright:")
            for f in sorted(missing):
                print(f"  - {f}")
            print("\nExpected format:")
            print("Copyright © Advanced Micro Devices, Inc., or its affiliates.")
            print("")
            print("SPDX-License-Identifier: MIT")
            print("\nRun with --fix to automatically add missing headers")
            sys.exit(1)
    elif not args.files:
        print("✅ All files have proper AMD copyright!")

    sys.exit(0)
