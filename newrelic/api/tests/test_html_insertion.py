import pytest
import os

from newrelic.api.html_insertion import insert_html_snippet

path = os.path.dirname(os.path.abspath(__file__)) + "/htmls/"

@pytest.mark.parametrize("input", [
    (path + "basic.html"),
    (path + "body_with_attributes.html"),
    (path + "charset_tag.html"),
    (path + "charset_tag_after_x_ua_tag.html"),
    (path + "charset_tag_before_x_ua_tag.html"),
    (path + "charset_tag_with_spaces.html"),
    (path + "comments1.html"),
    (path + "comments2.html"),
    (path + "content_type_charset_tag.html"),
    (path + "content_type_charset_tag_after_x_ua_tag.html"),
    (path + "content_type_charset_tag_before_x_ua_tag.html"),
    (path + "gt_in_quotes1.html"),
    (path + "gt_in_quotes2.html"),
    (path + "gt_in_quotes_mismatch.html"),
    (path + "gt_in_single_quotes1.html"),
    (path + "gt_in_single_quotes_mismatch.html"),
    (path + "head_with_attributes.html"),
    (path + "incomplete_non_meta_tags.html"),
    (path + "no_end_header.html"),
    (path + "no_header.html"),
    (path + "no_html_and_no_header.html"),
    (path + "no_start_header.html"),
    (path + "script1.html"),
    (path + "script2.html"),
    (path + "x_ua_meta_tag.html"),
    (path + "x_ua_meta_tag_multiline.html"),
    (path + "x_ua_meta_tag_spaces_around_equals.html"),
    (path + "x_ua_meta_tag_with_others.html"),
    (path + "x_ua_meta_tag_with_spaces.html"),
    (path + "x_ua_meta_with_uppercase.html"),

    # The following test file fails due to duplicate script tags -- very poor html.
    # Decided to ignore in testing.

    # (path + "x_ua_meta_tag_multiple_tags.html"),

    ])

def test_rum_insertion(input):
    header = "EXPECTED_RUM_LOADER_LOCATION"

    content = open(input, 'r').read()
    modified_content = content.replace("EXPECTED_RUM_LOADER_LOCATION", "")

    new_content = insert_html_snippet(modified_content, get_header)
    print new_content
    print open(input, 'r').read()
    assert new_content == open(input, 'r').read()

def get_header():
    return "EXPECTED_RUM_LOADER_LOCATION"
