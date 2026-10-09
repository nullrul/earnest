"""Tests for the Gherkin host adapter."""

import pytest

from earnest.adapters import gherkin
from earnest.index import Line


def test_tag_lines_are_read_and_comments_and_doc_strings_are_text():
    text = (
        "Feature: F\n\n  @stest:feat~a~1 @smoke\n  Scenario: S\n    Given a note\n"
        '      """\n      @stest:feat~b~1\n      """\n'
        "    And a snippet\n      ```markdown\n      @stest:feat~c~1\n      ```\n"
        "  # @stest:feat~d~1\n  @stest:feat~e~1\n"
    )
    assert gherkin.scan(text) == (Line(3, "  @stest:feat~a~1 @smoke"), Line(14, "  @stest:feat~e~1"))


def test_a_doc_string_closes_on_a_delimiter_line_with_a_comment_after_it():
    text = '  Given a note\n  """\n  @stest:feat~a~1\n  """ # end\n  @stest:feat~b~1\n'
    assert gherkin.scan(text) == (Line(5, "  @stest:feat~b~1"),)


def test_a_delimiter_in_a_description_opens_no_doc_string():
    text = 'Feature: F\n  """Quoted""" is the product\'s tagline.\n\n  @stest:feat~a~1\n  Scenario: S\n'
    assert gherkin.scan(text) == (Line(4, "  @stest:feat~a~1"),)


@pytest.mark.parametrize("space", [" ", "\t"], ids=["space", "tab"])
def test_a_tag_line_ends_at_its_first_hash_after_whitespace(space):
    assert gherkin.scan(f"@stest:feat~f~2{space}# was @stest:feat~f~1\n") == (Line(1, "@stest:feat~f~2"),)
