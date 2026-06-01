"""
Maya Scene Virus Cleaner
========================
Strips the ALA / Phage / vaccine family of Maya scene viruses from
.ma and .mb files. Runs OUTSIDE Maya — just plain Python, so it can
process a whole folder in seconds without opening each file.

Signs of infection it targets:
  - script nodes containing `open("...userSetup.py", "w")`
  - script nodes importing `os`, `subprocess`, `base64` combined with
    file-write operations
  - known virus marker strings (vaccine, phage, breed_gene, fuckVirus,
    sceneVaccine, leukocyte)

WORKFLOW:
  1. BACK UP your animation folder first (copy the whole E:/BlackAnimations
     to E:/BlackAnimations_backup). This script modifies files in place.
  2. Set ANIMATION_FOLDER below to the folder you want to clean.
  3. Run with:    python maya_virus_cleaner.py
     (or in Maya: exec(open(r'path/to/maya_virus_cleaner.py').read()))
  4. First run is DRY_RUN = True, only reports. Change to False to actually
     clean.

What it does:
  - For .ma (ASCII):  removes virus scriptNode blocks in-place.
  - For .mb (BINARY): finds the virus payload bytes and zeroes them out,
    which breaks the script without corrupting the rig data.
  - Writes a .bak alongside each cleaned file (plus the folder-level
    backup you should have made).
"""

import os
import re
import shutil
import sys

# -----------------------------------------------------------------------------
# CONFIG — edit these two
# -----------------------------------------------------------------------------
ANIMATION_FOLDER = r"E:\BlackAnimations"
DRY_RUN = True   # True = only report, don't modify. Set False to clean.
# -----------------------------------------------------------------------------


# Known virus marker strings. If a script node's source contains ANY of these,
# the node gets stripped. Conservative: we only remove nodes whose source has
# at least one of these patterns.
VIRUS_MARKERS = [
    b"userSetup.py",
    b"vaccine",
    b"fuckVirus",
    b"Phage",
    b"phage",
    b"breed_gene",
    b"leukocyte",
    b"sceneVaccine",
    b"pymel.internal.startup",     # used by some variants for persistence
    b"exec(base64.b64decode",       # classic obfuscation marker
    b"cmds.internalVar(userAppDir",  # virus needs this to find userSetup.py
]


# =============================================================================
# ASCII .ma cleaner
# =============================================================================
def clean_ma(path):
    """Strip virus scriptNode blocks from a Maya ASCII file.

    .ma files are plain text. A script node looks like:
        createNode script -n "vaccine_gene";
            ...
            setAttr ".b" -type "string" "<python source>";
            setAttr ".stp" 1;
    We scan each createNode script block, check its source for virus markers,
    and if found, delete the entire block.
    """
    with open(path, "rb") as f:
        data = f.read()

    if not any(marker in data for marker in VIRUS_MARKERS):
        return False, "clean"

    # Split into "createNode" chunks. A new top-level command starts at a
    # line beginning with a letter and ending with semicolon. We use a
    # conservative regex that captures script-node blocks specifically.
    #
    # Pattern: createNode script -n "NAME" ... ; (with optional parent flag)
    # followed by any number of continuation lines (starting with \t or spaces)
    # until the next top-level statement.
    text = data.decode("utf-8", errors="ignore")

    pattern = re.compile(
        r'^createNode\s+script\b[^\n]*\n'      # header line
        r'(?:[ \t].*\n)*',                      # indented continuation
        re.MULTILINE,
    )

    removed_nodes = []
    new_text_parts = []
    last_end = 0
    for m in pattern.finditer(text):
        block = m.group(0)
        # Does this script node contain any virus marker?
        block_bytes = block.encode("utf-8", errors="ignore")
        if any(marker in block_bytes for marker in VIRUS_MARKERS):
            # Record the node name for the report.
            name_match = re.search(r'-n\s+"([^"]+)"', block)
            removed_nodes.append(name_match.group(1) if name_match else "<unnamed>")
            # Keep everything before this block, skip the block itself.
            new_text_parts.append(text[last_end:m.start()])
            last_end = m.end()
    new_text_parts.append(text[last_end:])
    new_text = "".join(new_text_parts)

    if not removed_nodes:
        # Markers found outside any script node — shouldn't really happen for
        # ASCII, but don't touch the file in that case.
        return False, "markers found outside script nodes (manual review)"

    if DRY_RUN:
        return True, "would remove {} node(s): {}".format(
            len(removed_nodes), ", ".join(removed_nodes))

    # Make a .bak next to the original, then write the cleaned text.
    shutil.copy2(path, path + ".bak")
    with open(path, "wb") as f:
        f.write(new_text.encode("utf-8"))
    return True, "removed {} node(s): {}".format(
        len(removed_nodes), ", ".join(removed_nodes))


# =============================================================================
# BINARY .mb cleaner
# =============================================================================
# .mb format is a chunked binary file (IFF-style). Writing a proper .mb
# parser is complicated. What we can safely do without parsing: find any
# ASCII Python source containing virus markers and overwrite those byte
# ranges with spaces. The script payload then becomes a no-op when Maya
# reads it. We do NOT change the file length or move any bytes, so the
# IFF chunk offsets and lengths remain valid.

# Heuristic: script payloads are typically stored as null-terminated UTF-8
# strings inside the "scpt" attribute. We look for runs of printable-ASCII
# bytes that contain virus markers, and zap just those runs.

_PRINTABLE = set(range(0x20, 0x7F)) | {0x09, 0x0A, 0x0D}  # tab, LF, CR


def _find_printable_runs(data, min_len=40):
    """Yield (start, end) byte offsets of printable-ASCII runs >= min_len."""
    n = len(data)
    i = 0
    while i < n:
        if data[i] in _PRINTABLE:
            j = i
            while j < n and data[j] in _PRINTABLE:
                j += 1
            if j - i >= min_len:
                yield i, j
            i = j
        else:
            i += 1


def clean_mb(path):
    """Strip virus Python payloads from a Maya Binary file by overwriting
    the payload bytes with spaces. Keeps chunk lengths intact."""
    with open(path, "rb") as f:
        data = bytearray(f.read())

    if not any(marker in data for marker in VIRUS_MARKERS):
        return False, "clean"

    infected_runs = []
    for start, end in _find_printable_runs(data, min_len=40):
        run = data[start:end]
        if any(marker in run for marker in VIRUS_MARKERS):
            infected_runs.append((start, end))

    if not infected_runs:
        return False, "markers found but no matching payload (manual review)"

    if DRY_RUN:
        total = sum(e - s for s, e in infected_runs)
        return True, "would zap {} payload(s) totalling {} bytes".format(
            len(infected_runs), total)

    # Overwrite each infected run with spaces (0x20). Same length, so the
    # .mb file's internal chunk sizes stay valid and the rig data is
    # untouched. Maya will see an empty/whitespace Python source on load.
    for start, end in infected_runs:
        for k in range(start, end):
            data[k] = 0x20

    shutil.copy2(path, path + ".bak")
    with open(path, "wb") as f:
        f.write(bytes(data))
    return True, "zapped {} payload(s)".format(len(infected_runs))


# =============================================================================
# Walker
# =============================================================================
def main():
    if not os.path.isdir(ANIMATION_FOLDER):
        print("ERROR: folder does not exist: {}".format(ANIMATION_FOLDER))
        return

    print("=" * 70)
    print(" Maya Scene Virus Cleaner")
    print(" Folder : {}".format(ANIMATION_FOLDER))
    print(" Mode   : {}".format("DRY RUN (no changes)" if DRY_RUN
                                 else "LIVE (files will be modified)"))
    print("=" * 70)

    cleaned = []
    infected_but_skipped = []
    scanned = 0

    for root, dirs, files in os.walk(ANIMATION_FOLDER):
        for fname in files:
            lower = fname.lower()
            if not (lower.endswith(".ma") or lower.endswith(".mb")):
                continue
            path = os.path.join(root, fname)
            scanned += 1
            try:
                if lower.endswith(".ma"):
                    changed, msg = clean_ma(path)
                else:
                    changed, msg = clean_mb(path)
            except Exception as e:
                print(" ERROR scanning {}: {}".format(path, e))
                continue

            if changed:
                cleaned.append((path, msg))
                print(" INFECTED  {}".format(path))
                print("           -> {}".format(msg))
            elif msg != "clean":
                infected_but_skipped.append((path, msg))
                print(" SUSPECT   {}".format(path))
                print("           -> {}".format(msg))

    print()
    print("=" * 70)
    print(" Scanned      : {}".format(scanned))
    print(" Infected     : {}".format(len(cleaned)))
    print(" Needs review : {}".format(len(infected_but_skipped)))
    if DRY_RUN:
        print()
        print(" DRY RUN — no files were changed.")
        print(" Set DRY_RUN = False at the top of this script to actually clean.")
    print("=" * 70)


if __name__ == "__main__":
    main()
