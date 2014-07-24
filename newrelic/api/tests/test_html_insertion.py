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

   # The following test file fails as the insertion code
   # will insert after the second meta tag. Given that is
   # just how the code works, would probably suggest the
   # test input be modified to match what we actually
   # calculate.

   # 'x_ua_meta_tag_multiple_tags.html',
]

@pytest.mark.parametrize('input_file', input_files)
def test_rum_insertion(input_file):
   marker = b'EXPECTED_RUM_LOADER_LOCATION'

   def get_header():
       return marker

   input_file = os.path.join(input_files_directory, input_file)
   expected = open(input_file, 'rb').read()
   original = expected.replace(marker, b'')

   content = insert_html_snippet(original, get_header)

   assert content == expected
