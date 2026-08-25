"""
Tests for the constant-recovery taint analysis.

Ported from _tests/analyzer/test_const_recovery.py, which imported the dead
`src.analyzer.*` layout. Two changes were needed:

- imports now point at services.parser.core
- FileContext takes config_root explicitly instead of reading os.environ["CONFIG_ROOT"],
  so the CONFIG_ROOT env patching in setUp/tearDown is gone

Run with:  cd backend/src && python -m pytest ../tests -v
"""

import unittest
from unittest.mock import MagicMock, mock_open, patch

from services.parser.core.const_recovery import (
    get_args_from_line,
    recover_used_constants,
)
from services.parser.core.context import FileContext, MacroContext

MOCK_ROOT = "/mock/config/root"


class TestConstRecovery(unittest.TestCase):

    # ==================== get_args_from_line ====================

    def test_get_args_from_line_with_use(self):
        line = 'Use "macro_name" "arg1" "arg 2" arg3'
        self.assertEqual(get_args_from_line(line), ['"arg1"', '"arg 2"', "arg3"])

    def test_get_args_from_line_without_use(self):
        line = 'rule_name "arg1" "arg 2" arg3'
        self.assertEqual(get_args_from_line(line), ['"arg1"', '"arg 2"', "arg3"])

    # ==================== recover_used_constants ====================

    @patch("builtins.open", new_callable=mock_open,
           read_data="< Macro test_macro $var1 >\nline1\n")
    def test_file_context_yields_no_constants(self, mock_file):
        directive = MagicMock()
        directive.Context = FileContext(
            file_path="mock_path", line_num=2, config_root=MOCK_ROOT
        )
        directive.type = "test_type"
        self.assertEqual(recover_used_constants(directive), set())

    @patch("builtins.open", new_callable=mock_open, read_data="""
        < Macro test_macro @var1 @var2>
           line1 bbbbbbb @var1
        </Macro>

        Use test_macro aaaaaa ${global_var2}
           """)
    def test_macro_context_without_constants(self, mock_file):
        macro_context = MacroContext(
            macro_name="test_macro",
            defined_in=FileContext(line_num=2, file_path="mock_path", config_root=MOCK_ROOT),
            used_in=FileContext(line_num=6, file_path="mock_path", config_root=MOCK_ROOT),
        )
        macro_context.line_num = 1
        directive = MagicMock()
        directive.Context = macro_context
        directive.type = "test_type"
        self.assertEqual(recover_used_constants(directive), set())

    @patch("builtins.open", new_callable=mock_open, read_data="""
        < Macro test_macro @var1 @var2>
           line1 ~{constant1} @var1
        </Macro>

        Use test_macro ${global_var1} ${global_var2}
           """)
    def test_constants_recovered_through_macro_argument(self, mock_file):
        """A constant passed at the call site is recovered via the tinted parameter."""
        macro_context = MacroContext(
            macro_name="test_macro",
            defined_in=FileContext(line_num=2, file_path="mock_path", config_root=MOCK_ROOT),
            used_in=FileContext(line_num=6, file_path="mock_path", config_root=MOCK_ROOT),
        )
        macro_context.line_num = 1
        directive = MagicMock()
        directive.Context = macro_context
        directive.type = "test_type"
        constants = recover_used_constants(directive)
        self.assertEqual(constants, {("", "constant1"), ("", "global_var1")})

    @patch("builtins.open", new_callable=mock_open, read_data="""
        < Macro test_macro @var1 @var2>
           SecRule ENV:SOME_VAR "@beginsWith b" "~{constant1} @var1"
        </Macro>

        Use test_macro ${global_var1} ${global_var2}
           """)
    def test_modsecurity_operator_is_not_treated_as_a_parameter(self, mock_file):
        """@beginsWith must not be mistaken for a macro parameter."""
        macro_context = MacroContext(
            macro_name="test_macro",
            defined_in=FileContext(line_num=2, file_path="mock_path", config_root=MOCK_ROOT),
            used_in=FileContext(line_num=6, file_path="mock_path", config_root=MOCK_ROOT),
        )
        macro_context.line_num = 1
        directive = MagicMock()
        directive.Context = macro_context
        directive.type = "test_type"
        constants = recover_used_constants(directive)
        self.assertEqual(constants, {("", "constant1"), ("", "global_var1")})

    # ==================== edge cases ====================

    @patch("builtins.open", new_callable=mock_open, read_data="")
    def test_missing_file_raises(self, mock_file):
        directive = MagicMock()
        directive.Context = FileContext(
            file_path="mock_path", line_num=1, config_root=MOCK_ROOT
        )
        directive.type = "test_type"
        with self.assertRaises(ValueError):
            recover_used_constants(directive)

    # TODO: multiline directives inside macro and file context


if __name__ == "__main__":
    unittest.main()
