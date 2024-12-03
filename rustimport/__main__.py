import argparse
import logging
import os
import re
import sys
from typing import List

from rustimport import build_all, build_filepath, settings
from rustimport.pre_processing import PyO3Template

rust_lib_template = """// rustimport:pyo3

use pyo3::prelude::*;

#[pyfunction]
fn say_hello() {
    println!("Hello from {{EXTENSION_NAME}}, implemented in Rust!")
}

// Uncomment the below to implement custom pyo3 binding code. Otherwise, 
// rustimport will generate it for you for all functions annotated with
// #[pyfunction] and all structs annotated with #[pyclass].
//
//#[pymodule]
//fn {{EXTENSION_NAME}}(_py: Python, m: &Bound<'_, PyModule>) -> PyResult<()> {
//    m.add_function(wrap_pyfunction!(say_hello, m)?)?;
//    Ok(())
//}
"""

cargo_toml_template = """[package]
name = "{{EXTENSION_NAME}}"
version = "0.1.0"
edition = "2021"


# ======================
#  pyo3 configuration: 
# ======================

# You can safely remove the code below to let rustimport define your 
# pyo3-configuration automatically. It's still possible to add other 
# configuration or dependencies, or overwrite specific parts here.
# rustimport will merge your Cargo.toml file into it's generated 
# default configuration.
[lib]
# The name of the native library. This is the name which will be used in Python to import the
# library (i.e. `import {{EXTENSION_NAME}}`).
name = "{{EXTENSION_NAME}}"
#
# "cdylib" is necessary to produce a shared library for Python to import from.
# Downstream Rust code (including code in `bin/`, `examples/`, and `examples/`) will not be able
# to `use {{EXTENSION_NAME}};` unless the "rlib" or "lib" crate type is also included, e.g.:
# crate-type = ["cdylib", "rlib"]
crate-type = ["cdylib"]

[dependencies]
pyo3 = { version = "{{PYO3_VERSION}}", features = ["extension-module"] }
"""


def create_extension(name: str, cwd: str = '.'):
    if not re.match(r'^[a-zA-Z]\w*(\.rs)?$', name):
        raise ValueError(f"Invalid extension name: {name}. The name may only contain letters (preferably lowercase), "
                         f"numbers and underscores and should start with a letter.")

    path = os.path.realpath(os.path.join(cwd, name))
    name = os.path.splitext(os.path.basename(name))[0]

    if path.endswith(".rs"):
        with open(path, 'w+') as f:
            f.write(rust_lib_template.replace('{{EXTENSION_NAME}}', name))
    else:
        src_dir = os.path.join(path, 'src')
        os.makedirs(src_dir)
        with open(os.path.join(src_dir, 'lib.rs'), 'w+') as f:
            f.write(rust_lib_template.replace('{{EXTENSION_NAME}}', name))
        with open(os.path.join(path, 'Cargo.toml'), 'w+') as f:
            f.write(cargo_toml_template
                    .replace('{{EXTENSION_NAME}}', name)
                    .replace('{{PYO3_VERSION}}', PyO3Template.PYO3_VERSION))
        with open(os.path.join(path, '.rustimport'), 'w+') as f:
            f.write("This is a marker-file to make this crate importable by rustimport.")


def _run_from_commandline(raw_args: List[str]):
    parser = argparse.ArgumentParser("rustimport")

    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Increase log verbosity."
    )
    parser.add_argument(
        "--quiet", "-q", action="store_true", help="Only print critical log messages."
    )

    subparsers = parser.add_subparsers(dest="action", required=True)

    build_parser = subparsers.add_parser(
        "build",
        help="Build one or more rust source files or crates.",
    )
    build_parser.add_argument(
        "root",
        help="The file or directory to build. If a directory is given, "
        "rustimport walks it recursively to build all eligible source "
        "files.",
        nargs="*",
    )
    build_parser.add_argument(
        "--force", "-f", action="store_true", help="Force rebuild."
    )
    build_parser.add_argument(
        "--release", "-r", action="store_true", help="Build release-optimized binaries (toggle's cargo's --release flag)."
    )

    new_parser = subparsers.add_parser(
        "new",
        help="Create a new crate or single-file extension ready to be imported with rustimport. If the specified "
             "name ends with \".rs\", a single-file extension is created, otherwise, a crate will be set up.",
    )
    new_parser.add_argument("path")

    args = parser.parse_args(raw_args[1:])

    ch = logging.StreamHandler()
    ch.setFormatter(CLILoggingFormatter())

    if args.quiet:
        logging.basicConfig(level=logging.CRITICAL, handlers=[ch])
    elif args.verbose:
        logging.basicConfig(level=logging.DEBUG, handlers=[ch])
    else:
        logging.basicConfig(level=logging.INFO, handlers=[ch])

    if args.action == "build":
        release = args.release or settings.compile_release_binaries
        force = args.force or settings.force_rebuild

        for path in args.root or ["."]:
            path = os.path.abspath(os.path.expandvars(path))
            if os.path.isfile(path):
                build_filepath(path, release=release, force_rebuild=force)
            elif os.path.isdir(path):
                build_all(path, release=release, force_rebuild=force)
            else:
                raise FileNotFoundError(f'The given root path "{path}" could not be found.')
    elif args.action == "new":
        create_extension(args.path)
    else:
        parser.print_usage()


class CLILoggingFormatter(logging.Formatter):
    grey = "\33[90m"
    blue = "\033[94m"
    yellow = "\033[93m"
    red = "\033[91m"
    bold = "\033[1m"
    reset = "\033[1;0m"

    format_tag = "[%(levelname)s]"  # "%(asctime)s - %(name)s - %(levelname)s - %(message)s (%(filename)s:%(lineno)d)"
    format_message = " %(message)s"

    FORMATS = {
        logging.DEBUG: grey + format_tag + reset + format_message,
        logging.INFO: blue + format_tag + reset + format_message,
        logging.WARNING: yellow + format_tag + reset + format_message,
        logging.ERROR: red + format_tag + reset + format_message,
        logging.CRITICAL: bold + red + format_tag + reset + format_message
    }
    COLORLESS_FORMAT = format_tag + format_message

    def format(self, record):
        if self.supports_color():
            log_fmt = self.FORMATS.get(record.levelno)
        else:
            log_fmt = self.COLORLESS_FORMAT
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)

    @staticmethod
    def supports_color():
        """
        Returns True if the running system's terminal supports color, and False
        otherwise.
        """
        # Taken from django: https://stackoverflow.com/questions/7445658/how-to-detect-if-the-console-does-support-ansi-escape-codes-in-python/22254892#22254892
        plat = sys.platform
        supported_platform = plat != 'Pocket PC' and (plat != 'win32' or
                                                      'ANSICON' in os.environ)
        # isatty is not always implemented, #6223.
        is_a_tty = hasattr(sys.stdout, 'isatty') and sys.stdout.isatty()
        return supported_platform and is_a_tty


if __name__ == "__main__":
    _run_from_commandline(sys.argv)
