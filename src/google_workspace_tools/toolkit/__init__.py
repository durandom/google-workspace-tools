"""Optional Agno toolkit integration for Google Workspace Tools.

This module provides GoogleDriveTools for use with Agno agents.
Requires the 'agno' extra: pip install google-workspace-tools[agno]
"""

# Conditional export - only available if agno is installed
try:
    from .gdrive import GoogleDriveTools

    __all__ = ["GoogleDriveTools"]
except ImportError:
    __all__ = []


def get_toolkit():
    """Get GoogleDriveTools class.

    Raises:
        ImportError: If agno is not installed.

    Returns:
        GoogleDriveTools class.
    """
    try:
        from .gdrive import GoogleDriveTools

        return GoogleDriveTools
    except ImportError as e:
        raise ImportError(
            "Agno toolkit requires the 'agno' extra. Install with: pip install google-workspace-tools[agno]"
        ) from e
