"""Filtering models for Gmail and Google Calendar exports."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class GmailSearchFilter(BaseModel):
    """Filter options for Gmail message search and export.

    Examples:
        # Search by query
        GmailSearchFilter(query="from:boss@example.com subject:meeting")

        # Date range filter
        GmailSearchFilter(
            after_date=datetime(2024, 1, 1),
            before_date=datetime(2024, 12, 31)
        )

        # Label filter
        GmailSearchFilter(labels=["INBOX", "IMPORTANT"])

        # Combined filters
        GmailSearchFilter(
            query="has:attachment",
            labels=["work"],
            max_results=50
        )
    """

    query: str = Field(
        default="",
        description="Gmail search query using Gmail search syntax "
        "(e.g., 'from:user@example.com', 'subject:meeting', 'has:attachment')",
    )
    after_date: datetime | None = Field(default=None, description="Only messages sent after this date")
    before_date: datetime | None = Field(default=None, description="Only messages sent before this date")
    labels: list[str] = Field(
        default_factory=list,
        description="Filter by Gmail labels (e.g., ['INBOX', 'IMPORTANT', 'work']). "
        "Use INBOX, SENT, DRAFT, SPAM, TRASH for system labels",
    )
    has_attachment: bool | None = Field(default=None, description="Filter messages with/without attachments")
    max_results: int = Field(default=100, ge=1, le=500, description="Maximum number of messages to fetch")
    include_spam_trash: bool = Field(
        default=False, description="Include messages from spam and trash. Default is False"
    )

    def build_query(self) -> str:
        """Build a Gmail search query string from filter parameters.

        Returns:
            Gmail API-compatible search query string.

        Examples:
            >>> filter = GmailSearchFilter(query="meeting", labels=["INBOX"])
            >>> filter.build_query()
            'meeting label:INBOX'
        """
        parts = []

        # Add user query first
        if self.query:
            parts.append(self.query)

        # Add date filters
        if self.after_date:
            # Format: after:YYYY/MM/DD
            parts.append(f"after:{self.after_date.strftime('%Y/%m/%d')}")

        if self.before_date:
            # Format: before:YYYY/MM/DD
            parts.append(f"before:{self.before_date.strftime('%Y/%m/%d')}")

        # Add label filters
        for label in self.labels:
            parts.append(f"label:{label}")

        # Add attachment filter
        if self.has_attachment is not None:
            if self.has_attachment:
                parts.append("has:attachment")
            else:
                parts.append("-has:attachment")

        return " ".join(parts) if parts else ""


class CalendarEventFilter(BaseModel):
    """Filter options for Google Calendar event search and export.

    Examples:
        # Date range filter
        CalendarEventFilter(
            time_min=datetime(2024, 1, 1),
            time_max=datetime(2024, 12, 31)
        )

        # Search by keyword
        CalendarEventFilter(query="sprint planning")

        # Specific calendar
        CalendarEventFilter(calendar_ids=["work@example.com"])

        # Combined filters
        CalendarEventFilter(
            time_min=datetime(2024, 1, 1),
            query="meeting",
            calendar_ids=["primary"],
            max_results=100
        )
    """

    time_min: datetime | None = Field(
        default=None, description="Lower bound (inclusive) for event start time. ISO 8601 format"
    )
    time_max: datetime | None = Field(
        default=None, description="Upper bound (exclusive) for event end time. ISO 8601 format"
    )
    calendar_ids: list[str] = Field(
        default_factory=lambda: ["primary"],
        description="List of calendar IDs to query. Use 'primary' for the user's primary calendar. "
        "Empty list means primary only",
    )
    query: str = Field(
        default="", description="Free text search query. Searches event summaries, descriptions, locations, attendees"
    )
    single_events: bool = Field(
        default=True, description="Whether to expand recurring events into individual instances. Default is True"
    )
    max_results: int = Field(default=250, ge=1, le=2500, description="Maximum number of events to return per calendar")
    order_by: Literal["startTime", "updated"] = Field(
        default="startTime",
        description="The order of the events returned. "
        "'startTime' requires singleEvents=True. 'updated' for modification time",
    )

    def get_calendar_ids(self) -> list[str]:
        """Get the list of calendar IDs to query.

        Returns:
            List of calendar IDs, defaulting to ['primary'] if empty.
        """
        return self.calendar_ids if self.calendar_ids else ["primary"]
