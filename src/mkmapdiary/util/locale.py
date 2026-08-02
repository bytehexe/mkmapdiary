import tzlocal


def auto_detect_locale() -> str | None:
    """Auto-detect the system locale.

    Reads the standard POSIX locale environment variables in precedence
    order (``LC_ALL``, ``LC_CTYPE``, ``LANG``) without mutating any
    process-global locale state. This intentionally avoids
    ``locale.getdefaultlocale()`` (deprecated, slated for removal in
    Python 3.15) and the ``setlocale()``/``getlocale()`` pair, since the
    latter would require calling ``setlocale()`` to have any locale to
    report, and this function must stay side-effect-free.

    Returns:
        The detected locale string (e.g., 'en_US.UTF-8') or None if detection
        fails or only carries no language information (e.g. 'C', 'POSIX').
    """
    import os

    for var in ("LC_ALL", "LC_CTYPE", "LANG"):
        value = os.environ.get(var)
        if not value:
            continue
        # The encoding suffix carries no language information, so "C.UTF-8"
        # is as language-less as a bare "C".
        if value.split(".")[0] in ("C", "POSIX"):
            return None
        return value
    return None


def get_language(locale_str: str) -> str:
    """Extract the language code from a locale string.

    Args:
        locale_str: The locale string (e.g., 'en_US').
    """
    return locale_str.split("_")[0]


def auto_detect_timezone() -> str | None:
    """Auto-detect the system timezone.

    Returns:
        The detected timezone string (e.g., 'Europe/Berlin') or None if detection fails.
    """
    try:
        tz = tzlocal.get_localzone()
        return str(tz)
    except Exception:
        return None
