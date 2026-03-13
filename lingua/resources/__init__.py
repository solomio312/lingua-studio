"""Application resources — icons, fonts, glossaries."""

import os

RESOURCES_DIR = os.path.dirname(os.path.abspath(__file__))


def resource_path(filename):
    """Get absolute path to a resource file."""
    return os.path.join(RESOURCES_DIR, filename)
