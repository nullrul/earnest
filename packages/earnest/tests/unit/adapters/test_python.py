"""Tests for the Python host adapter."""

from earnest.adapters import python
from earnest.index import Line


def test_comments_come_with_their_line_numbers_and_strings_stay_text():
    lines = python.scan('x = "# not a comment"  # [impl->req~a~1]\n\ny = """\n# inside a string\n"""  # second\n')
    assert lines == (Line(1, "# [impl->req~a~1]"), Line(5, "# second"))


def test_a_file_that_stops_tokenizing_keeps_the_comments_before_the_error():
    assert python.scan("# [impl->req~a~1]\ndef f(:\n    x = (\n") == (Line(1, "# [impl->req~a~1]"),)


def test_a_comment_after_a_lone_carriage_return_is_read_on_the_line_git_counts():
    assert python.scan("x = 1\r# [impl->req~r~1]\n") == (Line(1, "# [impl->req~r~1]"),)


def test_a_bad_dedent_keeps_the_comments_before_the_error():
    assert python.scan("# [impl->req~a~1]\nif 1:\n        x=1\n    y=2\n") == (Line(1, "# [impl->req~a~1]"),)


def test_code_lines_skip_comments_and_blank_lines():
    text = "# [impl->req~a~1]\nx = 1  # trailing\n\n    \n# second\ny = 2\n"
    assert python.code_lines(text) == frozenset({2, 6})


def test_code_lines_cover_every_line_of_a_multiline_string():
    assert python.code_lines('y = """\n# inside\nstill\n"""\n# done\n') == frozenset({1, 2, 3, 4})


def test_code_lines_keep_what_came_before_a_tokenize_error():
    assert python.code_lines("y = 1\nif 1:\n        x=1\n    y=2\n") == frozenset({1, 2, 3})
