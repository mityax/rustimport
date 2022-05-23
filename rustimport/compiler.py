import json
import logging
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from typing import Optional, List, Dict, Any

from rustimport import settings

_logger = logging.getLogger(__name__)


class Cargo:
    def __init__(self, executable_path: Optional[str] = None):
        self.executable_path = executable_path or settings.cargo_executable or require('cargo')

    @dataclass
    class BuildResult:
        artifact_path: Optional[str]
        exit_code: int
        success: bool
        error_output: List[str]
        compiler_messages: List[Dict[str, Any]]

    def build(self, crate_path: str,
              destination_path: Optional[str] = None,
              release: bool = False,
              suppress_output: bool = False,
              additional_args: Optional[List[str]] = None) -> BuildResult:
        """
        Runs `cargo build --lib` for the given `crate_path`.

        @param crate_path: The path of the crate's root directory (the directory containing Cargo.toml).
        @param destination_path: Copy the built library artifact to this folder or file path.
        @param release: Whether to build a release binary (toggles Cargo's "--release" flag)
        @param suppress_output: If true, no process output will be printed to stdout. In case of build failure,
                                the output will be collected and logged using `logging.error()` for debugging.
        @param additional_args: Additional command line arguments to supply to the cargo executable.
        """

        cmd = [
            self.executable_path, 'rustc',
            '--lib',
            '--message-format', 'json'
        ]

        if suppress_output:
            cmd.append("--quiet")
        if release:
            cmd.append('--release')
        if additional_args:
            cmd.extend(additional_args)

        _logger.debug(f'Building {crate_path}: {" ".join(cmd)}')

        proc = subprocess.Popen(
            cmd,
            cwd=crate_path,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE if suppress_output else None,
        )

        result = self.__handle_build_process(crate_path, proc)

        if not result.success and suppress_output:
            _logger.error(f"Compilation failed. Cargo build output:\n\n"
                          + '\n'.join(result.error_output) +
                          f"{proc.stderr.read().decode()}")

        _logger.info(f'Cargo exited with code {result.exit_code}.')

        if result.success and result.artifact_path and destination_path:
            _logger.info(f"Copying artifact {result.artifact_path} to {destination_path}")
            shutil.copy2(result.artifact_path, destination_path)

        return result

    @classmethod
    def __handle_build_process(cls, crate_path: str, proc: subprocess.Popen) -> BuildResult:
        """
        Handle json messages received from the given cargo process `proc`.

        This method extracts build processes main library's artifact path (the python extension), if possible.

        @return: A `Cargo.BuildResult`. Note that artifact_path might be `None` if extraction
                 fails (mostly in case of compilation errors).
        """

        abs_crate_path = os.path.realpath(crate_path).rstrip("/")

        artifact_path = None
        messages = []
        error_output = []

        while (exit_code := proc.poll()) is None:
            line = proc.stdout.readline()

            if line.strip():
                messages.append(message := json.loads(line))

                if message.get('reason') == 'compiler-artifact':
                    if os.path.dirname(message.get('manifest_path')) == abs_crate_path:
                        artifact_path = message['filenames'][0]
                elif message.get('reason') == 'compiler-message':
                    if not proc.stderr:
                        sys.stderr.write(message['message']['rendered'])
                    else:
                        error_output.append(message['message']['rendered'])

        return cls.BuildResult(
            success=exit_code == 0,
            exit_code=exit_code,
            compiler_messages=messages,
            error_output=error_output,
            artifact_path=artifact_path,
        )


def require(executable_name: str):
    path = shutil.which(executable_name)

    if path:
        return path
    else:
        sys.stderr.write(
            "Could not find the rust toolchain installation. Make sure it is installed and "
            "the `PATH` environment variable is set correctly.\n\n"
        )
        if os.name != 'nt':
            sys.stderr.write("You can install the toolchain like this:\n$ curl https://sh.rustup.rs | sh\n\n")
        else:
            sys.stderr.write(
                "To install the toolchain, visit https://forge.rust-lang.org/infra/other-installation-methods.html"
                "#other-ways-to-install-rustup\n\n"
            )

        raise FileNotFoundError(f'Could not find {executable_name} binary.')
