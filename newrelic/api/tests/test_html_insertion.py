import os
import pytest

from newrelic.api.html_insertion import (insert_html_snippet,
        verify_body_exists)

input_files_directory = os.path.join(os.path.dirname(
        os.path.abspath(__file__)), 'html_insertion')

input_files = [
    'basic.html',
    'body_with_attributes.html',
    'charset_tag.html',
    'charset_tag_after_x_ua_tag.html',
    'charset_tag_before_x_ua_tag.html',
    'charset_tag_with_spaces.html',
    'comments1.html',
    'comments2.html',
    'content_type_charset_tag.html',
    'content_type_charset_tag_after_x_ua_tag.html',
    'content_type_charset_tag_before_x_ua_tag.html',
    'gt_in_quotes1.html',
    'gt_in_quotes2.html',
    'gt_in_quotes_mismatch.html',
    'gt_in_single_quotes1.html',
    'gt_in_single_quotes_mismatch.html',
    'head_with_attributes.html',
    'incomplete_non_meta_tags.html',
    'no_end_header.html',
    'no_header.html',
    'no_html_and_no_header.html',
    'no_start_header.html',
    'script1.html',
    'script2.html',
    'x_ua_meta_tag.html',
    'x_ua_meta_tag_multiline.html',
    'x_ua_meta_tag_spaces_around_equals.html',
    'x_ua_meta_tag_with_others.html',
    'x_ua_meta_tag_with_spaces.html',
    'x_ua_meta_with_uppercase.html',
    'x_ua_meta_tag_multiple_tags.html',
]

@pytest.mark.parametrize('input_file', input_files)
def test_rum_insertion(input_file):
    # This tests where everything within search limit and length
    # of content also within the search limit.

    marker = b'EXPECTED_RUM_LOADER_LOCATION'

    def get_header():
        return marker

    search_limit = 10*1024

    input_file = os.path.join(input_files_directory, input_file)
    expected = open(input_file, 'rb').read()
    original = expected.replace(marker, b'')

    content = insert_html_snippet(original, get_header, search_limit)

    assert content == expected, ('expected=%r, modified=%r' %
            (expected, content))

@pytest.mark.parametrize('input_file', input_files)
def test_post_padded_rum_insertion(input_file):
    # This tests where everything within search limit but length
    # of content is greater than search limit.

    marker = b'EXPECTED_RUM_LOADER_LOCATION'

    def get_header():
        return marker

    search_limit = 10*1024

    input_file = os.path.join(input_files_directory, input_file)

    expected = open(input_file, 'rb').read()
    expected = expected + search_limit * b' '

    original = expected.replace(marker, b'')

    content = insert_html_snippet(original, get_header, search_limit)

    assert content == expected, ('expected=%r, modified=%r' %
            (expected, content))

@pytest.mark.parametrize('input_file', input_files)
def test_pre_padded_rum_insertion(input_file):
    # This tests where everything is outside of the search limit.
    # No actual insertion should be done.

    marker = b'EXPECTED_RUM_LOADER_LOCATION'

    def get_header():
        return marker

    search_limit = 10*1024

    input_file = os.path.join(input_files_directory, input_file)

    expected = open(input_file, 'rb').read()
    expected = search_limit * b' ' + expected

    original = expected.replace(marker, b'')

    content = insert_html_snippet(original, get_header, search_limit)

    assert content == original, ('expected=%r, modified=%r' %
            (original, content))

def test_empty_string_rum_insertion():
    # This tests insertion on empty string. Should return None as
    # no insertion could be done.

    marker = b'EXPECTED_RUM_LOADER_LOCATION'

    def get_header():
        return marker

    original = b''

    content = insert_html_snippet(original, get_header)

    assert content == None, ('expected=%r, modified=%r' %
            (original, None))

def test_no_body_rum_insertion():
    # This tests insertion on string with no body within the search
    # limit. Should return None as no insertion could be done.

    marker = b'EXPECTED_RUM_LOADER_LOCATION'

    def get_header():
        return marker

    original = b'<html><head></head></html>'

    content = insert_html_snippet(original, get_header)

    assert content == None, ('expected=%r, modified=%r' %
            (original, None))

def test_post_padded_no_body_rum_insertion():
    # This tests insertion on string with no body within the search
    # limit. Should return the original string.

    marker = b'EXPECTED_RUM_LOADER_LOCATION'

    def get_header():
        return marker

    search_limit = 256

    original = b'<html><head></head></html>'
    original = original + search_limit * b' '

    content = insert_html_snippet(original, get_header, search_limit)

    assert content == original, ('expected=%r, modified=%r' %
            (original, content))

def test_pre_padded_no_body_rum_insertion():
    # This tests insertion on string with no body within the search
    # limit. Should return the original string.

    marker = b'EXPECTED_RUM_LOADER_LOCATION'

    def get_header():
        return marker

    search_limit = 256

    original = b'<html><head></head></html>'
    original = search_limit * b' ' + original

    content = insert_html_snippet(original, get_header, search_limit)

    assert content == original, ('expected=%r, modified=%r' %
            (original, content))

def test_empty_string_rum_body_exists():
    # This tests search for body on empty string.

    original = b''

    assert not verify_body_exists(original)

def test_no_body_rum_body_exists():
    # This tests search for body on empty string.

    original = b'<html><head></head></html>'

    assert not verify_body_exists(original)

def test_body_rum_body_exists():
    # This tests search for body on empty string.

    original = b'<body>'

    assert verify_body_exists(original)

def test_body_whitespace_rum_body_exists():
    # This tests search for body on empty string.

    original = b'<body  >'

    assert verify_body_exists(original)

def test_body_attributes_rum_body_exists():
    # This tests search for body on empty string.

    original = b'<body attr="value">'

    assert verify_body_exists(original)

def test_body_attributes_whitespace_rum_body_exists():
    # This tests search for body on empty string.

    original = b'<body attr="value"  >'

    assert verify_body_exists(original)
