import logging
import unittest
from unittest.mock import MagicMock, patch

from athlete_number.utils.logger import setup_logger


class TestSetupLogger(unittest.TestCase):
    @patch("athlete_number.utils.logger.logging.getLogger")
    def test_setup_logger_default(self, mock_get_logger):
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        # Ensure no handlers initially
        mock_logger.handlers = []

        # Explicitly clear any handlers
        mock_logger.hasHandlers.return_value = False

        setup_logger()

        mock_get_logger.assert_called_once_with(None)
        mock_logger.setLevel.assert_called_once_with(logging.DEBUG)
        mock_logger.addHandler.assert_called_once()
        handler = mock_logger.addHandler.call_args[0][0]
        self.assertIsInstance(handler, logging.StreamHandler)

    @patch("athlete_number.utils.logger.logging.getLogger")
    @patch("athlete_number.utils.logger.logging.FileHandler")
    def test_setup_logger_log_to_file(self, mock_file_handler, mock_get_logger):
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        # Ensure no handlers initially
        mock_logger.handlers = []

        # Explicitly clear any handlers
        mock_logger.hasHandlers.return_value = False

        # Create instances of the mock handlers
        mock_file_handler_instance = mock_file_handler.return_value

        setup_logger(log_to_file=True)

        mock_get_logger.assert_called_once_with(None)
        mock_logger.setLevel.assert_called_once_with(logging.DEBUG)
        self.assertEqual(mock_logger.addHandler.call_count, 2)
        handler1 = mock_logger.addHandler.call_args_list[0][0][0]
        handler2 = mock_logger.addHandler.call_args_list[1][0][0]
        self.assertIsInstance(handler1, logging.StreamHandler)
        self.assertEqual(handler2, mock_file_handler_instance)
        mock_file_handler.assert_called_once_with("application.log")

    @patch("athlete_number.utils.logger.logging.getLogger")
    def test_setup_logger_with_filter(self, mock_get_logger):
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        # Ensure no handlers initially
        mock_logger.handlers = []

        # Explicitly clear any handlers
        mock_logger.hasHandlers.return_value = False

        filter_messages = ["filter this"]
        setup_logger(filter_messages=filter_messages)

        mock_get_logger.assert_called_once_with(None)
        mock_logger.setLevel.assert_called_once_with(logging.DEBUG)
        mock_logger.addHandler.assert_called_once()
        handler = mock_logger.addHandler.call_args[0][0]
        self.assertIsInstance(handler, logging.StreamHandler)
        self.assertEqual(len(handler.filters), 1)
        self.assertIsInstance(handler.filters[0], logging.Filter)

    @patch("athlete_number.utils.logger.logging.getLogger")
    def test_setup_logger_with_name_and_level(self, mock_get_logger):
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        # Ensure no handlers initially
        mock_logger.handlers = []

        # Explicitly clear any handlers
        mock_logger.hasHandlers.return_value = False

        setup_logger(name="test_logger", level=logging.WARNING)

        mock_get_logger.assert_called_once_with("test_logger")
        mock_logger.setLevel.assert_called_once_with(logging.WARNING)
        mock_logger.addHandler.assert_called_once()
        handler = mock_logger.addHandler.call_args[0][0]
        self.assertIsInstance(handler, logging.StreamHandler)


if __name__ == "__main__":
    unittest.main()
