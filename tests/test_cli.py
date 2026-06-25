import contextlib
import io
import unittest
from unittest.mock import patch

from qa_datalake.aws_pipeline import PipelineError
from qa_datalake.cli import main


class CliTests(unittest.TestCase):
    def test_expected_pipeline_error_has_concise_output(self) -> None:
        stderr = io.StringIO()

        with patch(
            "qa_datalake.cli._run",
            side_effect=PipelineError("A particao ja existe."),
        ):
            with contextlib.redirect_stderr(stderr):
                with self.assertRaises(SystemExit) as raised:
                    main()

        self.assertEqual(raised.exception.code, 1)
        self.assertEqual(stderr.getvalue(), "Erro: A particao ja existe.\n")
        self.assertNotIn("Traceback", stderr.getvalue())

    def test_unexpected_error_is_not_hidden(self) -> None:
        with patch("qa_datalake.cli._run", side_effect=RuntimeError("unexpected")):
            with self.assertRaisesRegex(RuntimeError, "unexpected"):
                main()


if __name__ == "__main__":
    unittest.main()
