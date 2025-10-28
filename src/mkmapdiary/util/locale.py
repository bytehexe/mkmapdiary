import tzlocal


def auto_detect_locale() -> str | None:
    """Auto-detect the system locale.

    Returns:
        The detected locale string (e.g., 'en_US.UTF-8') or None if detection fails.
    """
    import locale

    try:
        loc = locale.getdefaultlocale()
        if loc[0] is not None:
            return f"{loc[0]}.{loc[1]}" if loc[1] else loc[0]
        return None
    except Exception:
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
