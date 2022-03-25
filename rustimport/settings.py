import os
import tempfile
from typing import Optional

force_rebuild: bool = False
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

cache_dir: str = os.path.join(tempfile.gettempdir(), 'rustimport')
"""
A directory to store temporary files. By default this directory will be created
within the operating system's temporary directory, and thus will be cleared after
each reboot.

For faster compile times (incremental compilation) it might make sense
for a project to supply a permanent caching directory instead. If the specified
directory does not exist, it'll be created automatically.
"""
