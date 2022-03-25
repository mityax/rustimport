import hashlib
import logging
import glob
import os
import struct
from typing import List, Tuple, Optional

_TAG = b"rustimport"
_FMT = struct.Struct("q" + str(len(_TAG)) + "s")

logger = logging.getLogger(__name__)


def is_checksum_valid(extension_path: str, file_patterns: List[str]) -> bool:
    """
    Load the saved checksum from the extension file check if it matches the
    checksum computed from current source files.
    """
    old_checksum = _load_checksum_trailer(extension_path)
    if old_checksum is None:
        return False  # Already logged error in load_checksum_trailer.
    try:
        return old_checksum == _calc_cur_checksum(file_patterns)
    except OSError as e:
        logger.info(
            "Checksummed file not found while checking rustimport checksum "
            "(%s); rebuilding." % e
        )
        return False


def _load_checksum_trailer(extension_path: str) -> Optional[bytes]:
    try:
        with open(extension_path, "rb") as f:
            f.seek(-_FMT.size, 2)
            length, tag = _FMT.unpack(f.read(_FMT.size))
            if tag != _TAG:
                logger.info(
                    "The extension is missing the trailer tag and thus is missing"
                    " its checksum; rebuilding."
                )
                return None
            f.seek(-(_FMT.size + length), 2)
            return f.read(length)
    except FileNotFoundError:
        logger.info("Failed to find compiled extension; rebuilding.")
        return None


def checksum_save(extension_path: str, files: List[str]):
    """
    Calculate the module checksum and then write it to the end of the shared
    object.
    """
    _save_checksum_trailer(extension_path, _calc_cur_checksum(files))


def _save_checksum_trailer(extension_path: str, cur_checksum: bytes):
    # We can just append the checksum to the shared object; this is effectively
    # legal (see e.g. https://stackoverflow.com/questions/10106447).
    with open(extension_path, "ab") as file:
        file.write(
            cur_checksum + _FMT.pack(len(cur_checksum), _TAG)
        )


def _calc_cur_checksum(files: List[str]) -> bytes:
    checksums: List[Tuple[str, str]] = []

    all_files: List[str] = []

    for entity in files:
        if glob.has_magic(entity):
            for file in glob.iglob(entity, recursive=True):
                all_files.append(file)
        elif os.path.isdir(entity):
            for file in glob.iglob(os.path.join(entity, '**'), recursive=True):
                all_files.append(file)
        else:
            all_files.append(entity)

    for filepath in sorted(all_files):
        with open(filepath, "rb") as f:
            checksums.append((filepath, hashlib.md5(f.read()).hexdigest()))

    payload = '\n'.join(
        f'{p}:{c}' for p, c in checksums
    ).encode()

    logging.debug(f"Checksum payload: {payload}")

    return hashlib.md5(payload).hexdigest().encode()
