"""Tests for Google Docs comments and suggestions export."""

from unittest.mock import MagicMock, patch

import pytest

from google_workspace_tools.core.config import GoogleDriveExporterConfig
from google_workspace_tools.core.exporter import GoogleDriveExporter


@pytest.fixture
def exporter():
    """Create an exporter instance with default config."""
    config = GoogleDriveExporterConfig()
    return GoogleDriveExporter(config)


@pytest.fixture
def exporter_no_extras():
    """Create an exporter with comments and suggestions disabled."""
    config = GoogleDriveExporterConfig(include_comments=False, include_suggestions=False)
    return GoogleDriveExporter(config)


# ─── Comment formatting tests ─────────────────────────────────────


class TestFormatCommentsAsMarkdown:
    def test_empty_comments(self, exporter):
        result = exporter._format_comments_as_markdown([])
        assert result == ""

    def test_basic_comment(self, exporter):
        comments = [
            {
                "id": "c1",
                "author": "Alice",
                "content": "This needs revision.",
                "quoted_text": "some document text",
                "resolved": False,
                "created_time": "2024-01-15T10:00:00Z",
                "replies": [],
            }
        ]
        result = exporter._format_comments_as_markdown(comments)
        assert "## Comments" in result
        assert "### Comment by Alice (2024-01-15)" in result
        assert "> some document text" in result
        assert "This needs revision." in result
        assert "[Resolved]" not in result

    def test_resolved_comment(self, exporter):
        comments = [
            {
                "id": "c2",
                "author": "Bob",
                "content": "Done.",
                "quoted_text": "old text",
                "resolved": True,
                "created_time": "2024-02-20T12:00:00Z",
                "replies": [],
            }
        ]
        result = exporter._format_comments_as_markdown(comments)
        assert "[Resolved]" in result
        assert "### Comment by Bob (2024-02-20) [Resolved]" in result

    def test_orphaned_comment(self, exporter):
        comments = [
            {
                "id": "c3",
                "author": "Charlie",
                "content": "Where did this go?",
                "quoted_text": None,
                "resolved": False,
                "created_time": "2024-03-01T09:00:00Z",
                "replies": [],
            }
        ]
        result = exporter._format_comments_as_markdown(comments)
        assert "[Orphaned — original text deleted]" in result

    def test_threaded_comment(self, exporter):
        comments = [
            {
                "id": "c4",
                "author": "Alice",
                "content": "Please clarify this section.",
                "quoted_text": "ambiguous text",
                "resolved": False,
                "created_time": "2024-01-10T08:00:00Z",
                "replies": [
                    {
                        "author": "Bob",
                        "content": "I'll update it.",
                        "created_time": "2024-01-11T09:00:00Z",
                    },
                    {
                        "author": "Charlie",
                        "content": "Looks good now.",
                        "created_time": "2024-01-12T10:00:00Z",
                    },
                ],
            }
        ]
        result = exporter._format_comments_as_markdown(comments)
        assert "**Replies:**" in result
        assert "**Bob** (2024-01-11): I'll update it." in result
        assert "**Charlie** (2024-01-12): Looks good now." in result


# ─── Suggestion formatting tests ──────────────────────────────────


class TestFormatSuggestionsAsMarkdown:
    def test_empty_suggestions(self, exporter):
        result = exporter._format_suggestions_as_markdown([])
        assert result == ""

    def test_insertion_suggestion(self, exporter):
        suggestions = [
            {
                "suggestion_id": "suggest.abc123",
                "parts": [
                    {
                        "type": "insertion",
                        "content": "new text here",
                        "paragraph_context": "surrounding new text here paragraph",
                    }
                ],
            }
        ]
        result = exporter._format_suggestions_as_markdown(suggestions)
        assert "## Suggestions" in result
        assert "### suggest.abc123" in result
        assert '**Insert:** "new text here"' in result
        assert "Context: surrounding new text here paragraph" in result

    def test_deletion_suggestion(self, exporter):
        suggestions = [
            {
                "suggestion_id": "suggest.def456",
                "parts": [
                    {
                        "type": "deletion",
                        "content": "old text",
                        "paragraph_context": "before old text after",
                    }
                ],
            }
        ]
        result = exporter._format_suggestions_as_markdown(suggestions)
        assert "**Delete:** ~~old text~~" in result

    def test_grouped_suggestion(self, exporter):
        suggestions = [
            {
                "suggestion_id": "suggest.grouped1",
                "parts": [
                    {
                        "type": "deletion",
                        "content": "remove this",
                        "paragraph_context": "full paragraph context",
                    },
                    {
                        "type": "insertion",
                        "content": "add this instead",
                        "paragraph_context": "full paragraph context",
                    },
                ],
            }
        ]
        result = exporter._format_suggestions_as_markdown(suggestions)
        assert "~~remove this~~" in result
        assert '"add this instead"' in result
        # Both parts should be under the same suggestion heading
        assert result.count("### suggest.grouped1") == 1


# ─── _fetch_doc_extras tests ──────────────────────────────────────


class TestFetchDocExtras:
    def test_disabled_returns_empty(self, exporter_no_extras):
        # Should not call any API when both flags are False
        result = exporter_no_extras._fetch_doc_extras("some-doc-id")
        assert result == ""

    @patch.object(GoogleDriveExporter, "_fetch_comments")
    @patch.object(GoogleDriveExporter, "_fetch_suggestions")
    def test_comments_only(self, mock_suggestions, mock_comments):
        config = GoogleDriveExporterConfig(include_comments=True, include_suggestions=False)
        exp = GoogleDriveExporter(config)

        mock_comments.return_value = [
            {
                "id": "c1",
                "author": "Alice",
                "content": "Test",
                "quoted_text": "text",
                "resolved": False,
                "created_time": "2024-01-01T00:00:00Z",
                "replies": [],
            }
        ]

        result = exp._fetch_doc_extras("doc-id")
        assert "## Comments" in result
        assert "## Suggestions" not in result
        mock_suggestions.assert_not_called()

    @patch.object(GoogleDriveExporter, "_fetch_comments")
    @patch.object(GoogleDriveExporter, "_fetch_suggestions")
    def test_suggestion_failure_does_not_block_comments(self, mock_suggestions, mock_comments):
        config = GoogleDriveExporterConfig(include_comments=True, include_suggestions=True)
        exp = GoogleDriveExporter(config)

        mock_comments.return_value = [
            {
                "id": "c1",
                "author": "Alice",
                "content": "Test",
                "quoted_text": "text",
                "resolved": False,
                "created_time": "2024-01-01T00:00:00Z",
                "replies": [],
            }
        ]
        mock_suggestions.side_effect = Exception("API error")

        result = exp._fetch_doc_extras("doc-id")
        assert "## Comments" in result
        assert "## Suggestions" not in result


# ─── Suggestion extraction from raw API JSON ──────────────────────


class TestExtractSuggestionsFromDocJson:
    """Test that _fetch_suggestions correctly parses raw Docs API JSON."""

    def test_extract_from_raw_json(self):
        config = GoogleDriveExporterConfig()
        exp = GoogleDriveExporter(config)

        # Simulate the raw Docs API response with SUGGESTIONS_INLINE
        raw_doc = {
            "body": {
                "content": [
                    {
                        "paragraph": {
                            "elements": [
                                {
                                    "textRun": {
                                        "content": "Hello world",
                                    }
                                },
                                {
                                    "textRun": {
                                        "content": "inserted text",
                                        "suggestedInsertionIds": ["suggest.insert1"],
                                    }
                                },
                                {
                                    "textRun": {
                                        "content": "deleted text",
                                        "suggestedDeletionIds": ["suggest.delete1"],
                                    }
                                },
                            ]
                        }
                    }
                ]
            }
        }

        # Mock the docs_service — set _docs_service directly (the property caches here)
        mock_service = MagicMock()
        mock_service.documents.return_value.get.return_value.execute.return_value = raw_doc
        exp._docs_service = mock_service

        suggestions = exp._fetch_suggestions("test-doc-id")

        assert len(suggestions) == 2

        ids = {s["suggestion_id"] for s in suggestions}
        assert "suggest.insert1" in ids
        assert "suggest.delete1" in ids

        # Check the insertion
        insert_suggestion = next(s for s in suggestions if s["suggestion_id"] == "suggest.insert1")
        assert insert_suggestion["parts"][0]["type"] == "insertion"
        assert insert_suggestion["parts"][0]["content"] == "inserted text"

        # Check the deletion
        delete_suggestion = next(s for s in suggestions if s["suggestion_id"] == "suggest.delete1")
        assert delete_suggestion["parts"][0]["type"] == "deletion"
        assert delete_suggestion["parts"][0]["content"] == "deleted text"
