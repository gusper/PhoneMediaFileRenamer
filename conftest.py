"""
pytest configuration and fixtures for photo_renamer tests.
"""

import os
import shutil
import tempfile
from pathlib import Path
from datetime import datetime
import pytest


@pytest.fixture
def tmp_test_dir(tmp_path):
    """
    Create a temporary directory for test file operations.

    Returns:
        Path: Temporary directory path that will be cleaned up after test
    """
    return tmp_path


@pytest.fixture
def sample_test_files(tmp_path):
    """
    Copy real test files to a temporary directory for safe testing.

    Returns:
        dict: Dictionary mapping test file types to their paths
    """
    test_files_src = Path(__file__).parent / "TestFiles"
    test_files_dest = tmp_path / "test_media"

    # Copy the entire TestFiles directory structure
    if test_files_src.exists():
        shutil.copytree(test_files_src, test_files_dest)

    return {
        "root": test_files_dest,
        "jpg_with_exif": test_files_dest / "2017" / "01" / "IMG_0353.JPG",
        "mov_with_metadata": test_files_dest / "2017" / "01" / "IMG_0001.MOV",
        "png_no_metadata": test_files_dest / "2017" / "01" / "20170121_172334000_iOS.png",
        "heic_file": test_files_dest / "heictest.HEIC",
        "fail_case_1": test_files_dest / "fail 2020.jpg",
        "fail_case_2": test_files_dest / "fails with 2017 instead of 2012 date taken.jpg",
    }


@pytest.fixture
def empty_test_dir(tmp_path):
    """
    Create an empty temporary directory.

    Returns:
        Path: Empty temporary directory path
    """
    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()
    return empty_dir


@pytest.fixture
def nested_test_structure(tmp_path):
    """
    Create a nested directory structure with test files.

    Returns:
        Path: Root path of nested structure
    """
    root = tmp_path / "nested"

    # Create nested structure
    (root / "2023" / "January").mkdir(parents=True)
    (root / "2023" / "February").mkdir(parents=True)
    (root / "2024").mkdir(parents=True)

    # Create dummy files
    test_files = [
        root / "2023" / "January" / "IMG_001.jpg",
        root / "2023" / "January" / "VID_001.mov",
        root / "2023" / "February" / "IMG_002.jpg",
        root / "2024" / "IMG_003.jpg",
    ]

    for file_path in test_files:
        file_path.touch()
        # Set a known modification time
        timestamp = datetime(2023, 1, 15, 10, 30, 0).timestamp()
        os.utime(file_path, (timestamp, timestamp))

    return root


@pytest.fixture
def mock_exif_data():
    """
    Mock EXIF data structure as returned by PIL.

    Returns:
        dict: Mock EXIF data with common tags
    """
    from PIL.ExifTags import TAGS

    # Find tag IDs for common EXIF fields
    tag_ids = {name: tag_id for tag_id, name in TAGS.items()}

    return {
        tag_ids.get('DateTimeOriginal', 36867): "2023:01:15 14:30:45",
        tag_ids.get('DateTime', 306): "2023:01:15 14:30:45",
        tag_ids.get('Make', 271): "Apple",
        tag_ids.get('Model', 272): "iPhone 12",
    }


@pytest.fixture
def mock_video_metadata():
    """
    Mock video metadata as returned by ffprobe JSON output.

    Returns:
        dict: Mock ffprobe metadata structure
    """
    return {
        "format": {
            "filename": "test_video.mov",
            "duration": "10.5",
            "tags": {
                "creation_time": "2023-01-15T14:30:45.000000Z",
                "com.apple.quicktime.make": "Apple",
                "com.apple.quicktime.model": "iPhone 12"
            }
        },
        "streams": [
            {
                "codec_type": "video",
                "codec_name": "h264",
                "width": 1920,
                "height": 1080,
                "tags": {
                    "creation_time": "2023-01-15T14:30:45.000000Z"
                }
            }
        ]
    }


@pytest.fixture
def mock_video_metadata_alternative_format():
    """
    Mock video metadata with alternative date format.

    Returns:
        dict: Mock ffprobe metadata with different date format
    """
    return {
        "format": {
            "filename": "test_video.mp4",
            "duration": "5.2",
            "tags": {
                "date": "2023:01:15 14:30:45"
            }
        },
        "streams": []
    }


@pytest.fixture
def create_test_file_with_timestamp(tmp_path):
    """
    Factory fixture to create test files with specific timestamps.

    Returns:
        callable: Function to create files with timestamps
    """
    def _create_file(filename, timestamp_str, extension=".jpg"):
        """
        Create a test file with a specific timestamp.

        Args:
            filename (str): Base filename
            timestamp_str (str): Timestamp in "YYYY-MM-DD HH:MM:SS" format
            extension (str): File extension

        Returns:
            Path: Path to created file
        """
        file_path = tmp_path / f"{filename}{extension}"
        file_path.touch()

        # Parse and set timestamp
        dt = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
        timestamp = dt.timestamp()
        os.utime(file_path, (timestamp, timestamp))

        return file_path

    return _create_file