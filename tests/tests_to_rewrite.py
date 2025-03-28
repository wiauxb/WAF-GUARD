import unittest
from unittest.mock import patch, mock_open, MagicMock


class MyTestCase(unittest.TestCase):

    # Tests for convert_context_path
    def test_convert_context_path(self):
        path = "some/path/conf/example.conf"
        expected = "/mock/config/root/conf/example.conf"
        self.assertEqual(convert_context_path(path), expected)

    # Tests for find_line_inside_macro
    @patch("builtins.open", new_callable=mock_open, read_data="line1\nline2\nline3\n")
    def test_find_line_inside_macro_with_offset(self, mock_file):
        result = find_line_inside_macro("mock_path", 1, offset=1)
        self.assertEqual(result, "line2\n")

    @patch("builtins.open", new_callable=mock_open, read_data="line1\n#comment\nline2\nline3\n")
    def test_find_line_inside_macro_skip_comments(self, mock_file):
        result = find_line_inside_macro("mock_path", 1, offset=1)
        self.assertEqual(result, "line2\n")

    @patch("builtins.open", new_callable=mock_open, read_data="line1\nline2\nline3\n")
    def test_find_line_inside_macro_with_target(self, mock_file):
        result = find_line_inside_macro("mock_path", 1, target="line3")
        self.assertEqual(result, "line3\n")

    # Tests for parse_macro_def
    @patch("builtins.open", new_callable=mock_open, read_data="<Macro test_macro arg1 arg2>\n")
    def test_parse_macro_def(self, mock_file):
        name, args = parse_macro_def("mock_path", 1)
        self.assertEqual(name, "test_macro")
        self.assertEqual(args, ["arg1", "arg2"])

    @patch("builtins.open", new_callable=mock_open, read_data="< Macro test_macro arg1 arg2 >\n")
    def test_parse_macro_def(self, mock_file):
        name, args = parse_macro_def("mock_path", 1)
        self.assertEqual(name, "test_macro")
        self.assertEqual(args, ["arg1", "arg2"])

    @patch("builtins.open", new_callable=mock_open, read_data="invalid macro line\n")
    def test_parse_macro_def_invalid(self, mock_file):
        with self.assertRaises(Exception):
            parse_macro_def("mock_path", 1)


if __name__ == '__main__':
    unittest.main()
