"""Lingua — Professional Ebook Translation Studio."""

__version__ = '1.1.0'
__author__ = 'ManuX'
__app_name__ = 'Lingua'


# Identity functions replacing Calibre's i18n system
def _z(s):
    """Marker for lazy translation strings (identity in standalone)."""
    return s


def _(s):
    """Translation function (identity in standalone)."""
    return s
