import os
import pytest
import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch
from watchdog.events import FileCreatedEvent
from src.telegram_bot import parse_chat_id_from_filename, QRFileHandler, bot, QR_FOLDER

# Sample valid and invalid filenames
VALID_FILENAME = "qr_123456789_abcdef.png"
INVALID_FILENAME = "qr_invalid.png"

@pytest.mark.parametrize("filename, expected_chat_id", [
    (VALID_FILENAME, 123456789),
    (INVALID_FILENAME, None),
    ("qr_987654321_test.png", 987654321),
    ("qr_999_text_extra.png", 999),
    ("invalid_format.png", None),
])
def test_parse_chat_id_from_filename(filename, expected_chat_id):
    """
    Test that chat_id is correctly extracted from valid filenames and returns None for invalid ones.
    """
    chat_id = parse_chat_id_from_filename(filename)
    assert chat_id == expected_chat_id


@patch("src.qr_watcher.bot.send_photo", new_callable=AsyncMock)
@patch("os.path.getsize", return_value=100)  # Simulate non-empty file
@patch("os.remove")  # Prevent actual file deletion
@pytest.mark.asyncio
async def test_on_created(mock_remove, mock_getsize, mock_send_photo):
    """
    Test the on_created method of QRFileHandler by simulating file creation.
    """
    handler = QRFileHandler()
    
    # Create a mock event for a new file
    file_path = os.path.join(QR_FOLDER, VALID_FILENAME)
    event = FileCreatedEvent(file_path)
    
    # Ensure the event is handled correctly
    with patch("builtins.open", MagicMock()):
        handler.on_created(event)

    # Allow time for async operations
    await asyncio.sleep(1)
    
    # Verify that the bot attempted to send a photo
    mock_send_photo.assert_called_once()
    assert mock_send_photo.call_args[1]["chat_id"] == 123456789
    assert "photo" in mock_send_photo.call_args[1]

    # Verify that the file was "deleted"
    mock_remove.assert_called_once_with(file_path)


def test_on_created_invalid_filename():
    """
    Test that QRFileHandler correctly rejects invalid filenames.
    """
    handler = QRFileHandler()
    event = FileCreatedEvent(os.path.join(QR_FOLDER, INVALID_FILENAME))
    
    with patch("src.qr_watcher.logger.error") as mock_logger:
        handler.on_created(event)
        mock_logger.assert_called_with("Could not parse chat id from filename: %s", INVALID_FILENAME)


@patch("watchdog.observers.Observer.schedule")
@patch("watchdog.observers.Observer.start")
def test_start_watcher(mock_start, mock_schedule):
    """
    Test that the folder watcher starts correctly.
    """
    with patch("src.qr_watcher.Observer", MagicMock()) as mock_observer:
        from src.qr_watcher import start_watcher

        with patch("time.sleep", side_effect=KeyboardInterrupt):  # Simulate stopping
            start_watcher()

        mock_observer.return_value.schedule.assert_called_once()
        mock_observer.return_value.start.assert_called_once()
