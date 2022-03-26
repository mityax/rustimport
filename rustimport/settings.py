import hashlib
import os
import tempfile
from typing import Optional

force_rebuild: bool = os.getenv("RUSTIMPORT_FORCE_REBUILD", "0").lower() in ("true", "yes", "1")
"""Whether to force rebuild on each import or not."""

release_mode: bool = os.getenv("RUSTIMPORT_RELEASE_MODE", "0").lower() in ("true", "yes", "1")
"""Whether to compile optimized release binaries or not (toggles cargo's "--release" flag)."""

cargo_executable: Optional[str] = os.getenv("RUSTIMPORT_CARGO_EXECUTABLE")
"""The cargo executable path to use."""

rtld_flags: int = 0
"""
It can be useful to set rtld_flags to RTLD_GLOBAL. This allows
extensions that are loaded later to share the symbols from this
extension. This is primarily useful in a project where several
interdependent extensions are loaded but it's undesirable to combine
the multiple extensions into a single extension.
"""

cache_dir: str = os.getenv('RUSTIMPORT_CACHE_DIR') or os.path.join(tempfile.gettempdir(), 'rustimport')
"""
A directory to store temporary files. By default this directory will be created
within the operating system's temporary directory, and thus will be cleared after
each reboot.

For faster compile times (incremental compilation) it might make sense
for a project to supply a permanent caching directory instead. If the specified
directory does not exist, it'll be created automatically.
"""

checksum_hasher = hashlib.sha1
"""
Specify the hash function to use for hashing. This function should be compatible with all the named
constructors from `hashlib` (e.g. `hashlib.md5(...)`  or `hashlib.sha256(...)`).

By default, sha1 is used as it has the [best performance](https://github.com/SharkyRawr/python-hashlib-benchmark)
and is [reasonably collision-proof](https://crypto.stackexchange.com/a/2584).
"""