"""Tests for _nest_gdocs_flat_lists HTML preprocessing."""

import pytest

from google_workspace_tools.core.exporter import _nest_gdocs_flat_lists


@pytest.mark.unit
class TestNestGdocsFlatLists:
    """Tests for Google Docs flat list nesting preprocessor."""

    def test_two_level_nesting(self):
        """Level-0 and level-1 items produce nested markdown lists."""
        html = """<html><body>
        <ul class="lst-kix_abc123-0 start"><li>Top item</li></ul>
        <ul class="lst-kix_abc123-1 start"><li>Sub item</li></ul>
        </body></html>"""
        result = _nest_gdocs_flat_lists(html)
        # The level-1 <ul> should now be nested inside the level-0 <li>
        assert "<li>Top item<ul><li>Sub item</li></ul></li>" in result.replace("\n", "")

    def test_three_level_nesting(self):
        """Level-0, level-1, and level-2 items nest correctly."""
        html = """<html><body>
        <ul class="lst-kix_abc123-0 start"><li>L0</li></ul>
        <ul class="lst-kix_abc123-1 start"><li>L1</li></ul>
        <ul class="lst-kix_abc123-2 start"><li>L2</li></ul>
        </body></html>"""
        result = _nest_gdocs_flat_lists(html)
        assert "<li>L0<ul><li>L1<ul><li>L2</li></ul></li></ul></li>" in result.replace(
            "\n", ""
        )

    def test_return_to_parent_level(self):
        """Going from level-1 back to level-0 creates sibling top-level items."""
        html = """<html><body>
        <ul class="lst-kix_abc123-0 start"><li>First top</li></ul>
        <ul class="lst-kix_abc123-1 start"><li>Sub</li></ul>
        <ul class="lst-kix_abc123-0"><li>Second top</li></ul>
        </body></html>"""
        result = _nest_gdocs_flat_lists(html)
        # Both top-level items should be direct children of the root <ul>
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(result, "html.parser")
        root_ul = soup.find("ul")
        top_lis = root_ul.find_all("li", recursive=False)
        assert len(top_lis) == 2
        assert "First top" in top_lis[0].get_text()
        assert "Second top" in top_lis[1].get_text()

    def test_multiple_items_at_same_level(self):
        """Multiple consecutive items at the same sub-level stay siblings."""
        html = """<html><body>
        <ul class="lst-kix_abc123-0 start"><li>Parent</li></ul>
        <ul class="lst-kix_abc123-1 start">
          <li>Child A</li>
          <li>Child B</li>
          <li>Child C</li>
        </ul>
        </body></html>"""
        result = _nest_gdocs_flat_lists(html)
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(result, "html.parser")
        root_ul = soup.find("ul")
        parent_li = root_ul.find("li", recursive=False)
        nested_ul = parent_li.find("ul", recursive=False)
        assert nested_ul is not None
        children = nested_ul.find_all("li", recursive=False)
        assert len(children) == 3

    def test_separate_list_ids_stay_independent(self):
        """Lists with different kix IDs separated by non-list elements remain independent."""
        html = """<html><body>
        <ul class="lst-kix_list1-0 start"><li>List 1</li></ul>
        <p>Separator</p>
        <ul class="lst-kix_list2-0 start"><li>List 2</li></ul>
        </body></html>"""
        result = _nest_gdocs_flat_lists(html)
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(result, "html.parser")
        uls = soup.find_all("ul")
        assert len(uls) == 2

    def test_non_gdocs_html_unchanged(self):
        """Regular HTML without Google Docs list classes passes through unmodified."""
        html = "<html><body><ul><li>Normal list</li></ul></body></html>"
        result = _nest_gdocs_flat_lists(html)
        assert "<li>Normal list</li>" in result

    def test_no_body_tag_returns_input(self):
        """HTML without a <body> tag returns input unchanged."""
        html = "<div>no body</div>"
        assert _nest_gdocs_flat_lists(html) == html

    def test_preserves_links_in_list_items(self):
        """Links and other inline markup inside <li> are preserved."""
        html = """<html><body>
        <ul class="lst-kix_abc123-0 start">
          <li><a href="https://example.com">Link text</a></li>
        </ul>
        <ul class="lst-kix_abc123-1 start">
          <li><span style="font-weight:bold">Bold sub</span></li>
        </ul>
        </body></html>"""
        result = _nest_gdocs_flat_lists(html)
        assert 'href="https://example.com"' in result
        assert "Bold sub" in result

    def test_markdown_output_is_indented(self):
        """End-to-end: nested Google Docs HTML produces indented markdown."""
        from html_to_markdown import convert_to_markdown

        html = """<html><body>
        <ul class="lst-kix_abc123-0 start"><li>Top</li></ul>
        <ul class="lst-kix_abc123-1 start"><li>Middle</li></ul>
        <ul class="lst-kix_abc123-2 start"><li>Deep</li></ul>
        </body></html>"""
        nested = _nest_gdocs_flat_lists(html)
        md = convert_to_markdown(nested)
        lines = [l for l in md.strip().splitlines() if l.strip()]
        # Top-level item should have no leading whitespace
        assert lines[0].lstrip() != lines[0] or lines[0].startswith("*") or lines[0].startswith("-")
        # Sub-items should be indented more than their parents
        assert len(lines) == 3
        indent_0 = len(lines[0]) - len(lines[0].lstrip())
        indent_1 = len(lines[1]) - len(lines[1].lstrip())
        indent_2 = len(lines[2]) - len(lines[2].lstrip())
        assert indent_1 > indent_0
        assert indent_2 > indent_1
