import hashlib
import importlib.util
import sys
import subprocess
import time
from importlib.machinery import ExtensionFileLoader
from pathlib import Path
from shutil import which

from IPython.core import magic_arguments
from IPython.core.magic import Magics, cell_magic, magics_class
from importlib.metadata import version

try:
    from IPython.paths import get_ipython_cache_dir
except ImportError:
    # older IPython version
    from IPython.utils.path import get_ipython_cache_dir


@magics_class
class RustImportIPython(Magics):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._loaded_module = set()
        rustc = which("rustc")
        self._rust_version = subprocess.check_output([rustc, "--version"]).decode(
            "utf8"
        )
        self._python_version = sys.version_info
        self._rustimport_version = version("rustimport")

    def _find_compiled_file(self, module_name, lib_path):
        # Find compiled file
        module_path = None
        for path in lib_path.iterdir():
            if path.name.startswith(module_name) and path.suffix != ".rs":
                module_path = path
                break
        return module_path

    @cell_magic
    @magic_arguments.magic_arguments()
    @magic_arguments.argument(
        "-r",
        "--release",
        action="store_true",
        default=False,
        help="Build release-optimized binaries (toggle's cargo's --release flag).",
    )
    @magic_arguments.argument(
        "-f",
        "--force",
        action="store_true",
        default=False,
        help="Force rebuild.",
    )
    @magic_arguments.argument(
        "--module-path-variable",
        type=str,
        default="",
        help="Variable to store path of module",
    )
    def rustimport(self, line: str, cell: str):
        args = magic_arguments.parse_argstring(self.rustimport, line)

        lib_path = Path(get_ipython_cache_dir()) / "rustimport"
        lib_path.mkdir(exist_ok=True)

        key = [
            cell,
            sys.version_info,
            sys.executable,
            args.release,
            args.module_path_variable,
            self._rust_version,
            self._python_version,
            self._rustimport_version,
        ]
        if args.force:
            # Add time to key to force the rebuild
            key.append(time.time())

        # Use a smaller hash to prevent Windows issue with long file paths
        hashed_key = hashlib.shake_256(str(key).encode("utf-8")).hexdigest(8)
        module_name = f"_magic_{hashed_key}"

        # PyO3 only allows modules to be loaded once. If module name is already in
        # `_loaded_module`, then the code is already loaded and compilation can be
        # skipped.
        if module_name in self._loaded_module:
            module_path = str(self._find_compiled_file(module_name, lib_path))
            if args.module_path_variable:
                self.shell.push({args.module_path_variable: module_path})
            return

        module_file = lib_path / f"{module_name}.rs"

        cell = f"""// rustimport:pyo3\n{cell}"""
        module_file.write_text(cell)

        # Lazy load here because of circular imports
        from rustimport import build_filepath

        build_filepath(str(module_file), release=args.release)
        module_path = str(self._find_compiled_file(module_name, lib_path))

        # Load module dynamically
        spec = importlib.util.spec_from_file_location(
            module_name, loader=ExtensionFileLoader(str(module_name), module_path)
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self._loaded_module.add(module_name)

        # import all
        module_dict = module.__dict__
        if "__all__" in module_dict:
            keys = module_dict["__all__"]
        else:
            keys = [k for k in module_dict if not k.startswith("_")]

        for k in keys:
            self.shell.push({k: module_dict[k]})

        if args.module_path_variable:
            self.shell.push({args.module_path_variable: module_path})
