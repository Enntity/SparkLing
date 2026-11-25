# SPDX-License-Identifier: AGPL-3.0-only
"""Drop the page cache of files under the given directories (POSIX_FADV_DONTNEED; no root needed)."""
import os, sys
n = 0
for d in sys.argv[1:]:
    for root, _, files in os.walk(d):
        for f in files:
            try:
                fd = os.open(os.path.join(root, f), os.O_RDONLY)
                os.posix_fadvise(fd, 0, 0, os.POSIX_FADV_DONTNEED)
                os.close(fd)
                n += 1
            except OSError:
                pass
print("evicted", n, "files")
