import unittest
from unittest.mock import patch, mock_open, MagicMock
import os
from src.analyzer.const_recovery import (
    get_args_from_line,
    recover_used_constants,
)
from src.analyzer.helper_classes.context import FileContext, MacroContext
from src.analyzer.helper_classes.directives import Directive


class TestConstRecovery(unittest.TestCase):
    def setUp(self):
        self.mock_config_root = "/mock/config/root"
        self.env_patcher = patch.dict(os.environ, {"CONFIG_ROOT": self.mock_config_root})
        self.env_patcher.start()

    def tearDown(self):
        self.env_patcher.stop()

    # Tests for get_args_from_line
    def test_get_args_from_line_with_use(self):
        line = 'Use "macro_name" "arg1" "arg 2" arg3'
        self.assertEqual(get_args_from_line(line), ['"arg1"', '"arg 2"', "arg3"])

    def test_get_args_from_line_without_use(self):
        line = 'rule_name "arg1" "arg 2" arg3'
        self.assertEqual(get_args_from_line(line), ['"arg1"', '"arg 2"', "arg3"])

    # Tests for recover_used_constants
    @patch("builtins.open", new_callable=mock_open, read_data="< Macro test_macro $var1 >\nline1\n")
    def test_recover_used_constants_file_context(self, mock_file):
        directive = MagicMock()
        directive.Context = FileContext(file_path="mock_path", line_num=2)
        directive.type = "test_type"
        constants = recover_used_constants(directive)
        self.assertEqual(constants, set())

    @patch("builtins.open", new_callable=mock_open, read_data="""
        < Macro test_macro @var1 @var2>
           line1 bbbbbbb @var1
        </Macro>
           
        Use test_macro aaaaaa ${global_var2}
           """)
    def test_recover_used_constants_macro_context(self, mock_file):
        macro_context = MacroContext(
            macro_name="test_macro",
            defined_in=FileContext(line_num=2, file_path="mock_path"),
            used_in=FileContext(line_num=6, file_path="mock_path")
        )
        macro_context.line_num = 1
        directive = MagicMock()
        directive.Context = macro_context
        directive.type = "test_type"
        constants = recover_used_constants(directive)
        self.assertEqual(constants, set())

    @patch("builtins.open", new_callable=mock_open, read_data="""
        < Macro test_macro @var1 @var2>
           line1 ~{constant1} @var1
        </Macro>
           
        Use test_macro ${global_var1} ${global_var2}
           """)
    def test_recover_used_constants_with_constants(self, mock_file):
        macro_context = MacroContext(
            macro_name="test_macro",
            defined_in=FileContext(line_num=2, file_path="mock_path"),
            used_in=FileContext(line_num=6, file_path="mock_path")
        )
        macro_context.line_num = 1
        directive = MagicMock()
        directive.Context = macro_context
        directive.type = "test_type"
        constants = recover_used_constants(directive)
        self.assertEqual(constants, {"constant1", "global_var1"})

    @patch("builtins.open", new_callable=mock_open, read_data="""
        < Macro test_macro @var1 @var2>
           SecRule ENV:SOME_VAR "@beginsWith b" "~{constant1} @var1"
        </Macro>

        Use test_macro ${global_var1} ${global_var2}
           """)
    def test_recover_used_constants_with_operator(self, mock_file):
        macro_context = MacroContext(
            macro_name="test_macro",
            defined_in=FileContext(line_num=2, file_path="mock_path"),
            used_in=FileContext(line_num=6, file_path="mock_path")
        )
        macro_context.line_num = 1
        directive = MagicMock()
        directive.Context = macro_context
        directive.type = "test_type"
        constants = recover_used_constants(directive)
        self.assertEqual(constants, {"constant1", "global_var1"})

    # Edge case tests
    @patch("builtins.open", new_callable=mock_open, read_data="")
    def test_recover_used_constants_missing_file(self, mock_file):
        directive = MagicMock()
        directive.Context = FileContext(file_path="mock_path", line_num=1)
        directive.type = "test_type"
        with self.assertRaises(ValueError):
            recover_used_constants(directive)

    #TODO: multiline directives inside macro and file context

if __name__ == "__main__":
    unittest.main()
