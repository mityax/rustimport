from typing import List


class BuildError(Exception):
    """Raised if building a native rust extension fails for any reason."""


_potential_reasons = []


def notify_potential_failure_reason(reason: str):
    """
    Notify the error handling system about a potential reason for a failed import, e.g.
    that a file does not contain the "// rustimport" marker, but would be a valid
    candidate otherwise.
    """

    _potential_reasons.append(reason)


def get_potential_failure_reasons() -> List[str]:
    """
    Retrieve a list of all collected potential failure reasons.
    """

    return list(_potential_reasons)
