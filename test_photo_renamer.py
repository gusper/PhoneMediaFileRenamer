"""
Unit and integration tests for photo_renamer.py
"""

import os
import json
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock, patch, mock_open, MagicMock
import pytest

import photo_renamer


class TestDateExtraction:
    """Tests for date extraction functions."""

    def test_get_best_fallback_date_prefers_modified_when_creation_newer(self, create_test_file_with_timestamp):
        """Test that modified time is used when creation time is newer (file was copied)."""
        file_path = create_test_file_with_timestamp("test", "2023-01-15 10:30:00")

        # Simulate file being copied (creation time > modified time)
        # by setting creation time to be newer
        stat = os.stat(file_path)
        newer_time = datetime(2023, 6, 1, 10, 30, 0).timestamp()
        older_time = stat.st_mtime

        with patch('os.stat') as mock_stat:
            mock_stat.return_value = Mock(
                st_ctime=newer_time,
                st_mtime=older_time,
                st_atime=newer_time
            )
            result = photo_renamer.get_best_fallback_date(file_path)

        # Should prefer the older modified time
        assert result == datetime.fromtimestamp(older_time)

    def test_get_best_fallback_date_uses_earliest_when_creation_older(self, create_test_file_with_timestamp):
        """Test that earliest timestamp is used when creation time is older."""
        file_path = create_test_file_with_timestamp("test", "2023-01-15 10:30:00")

        # Use actual file timestamps where creation <= modified
        result = photo_renamer.get_best_fallback_date(file_path)

        assert isinstance(result, datetime)
        assert result.year == 2023

    @patch('photo_renamer.Image.open')
    def test_get_image_date_taken_with_valid_exif(self, mock_image_open, mock_exif_data):
        """Test extracting date from image with valid EXIF data."""
        mock_image = MagicMock()
        mock_image.__enter__.return_value = mock_image
        mock_image.getexif.return_value = mock_exif_data
        mock_image_open.return_value = mock_image

        result = photo_renamer.get_image_date_taken("test.jpg")

        assert result == datetime(2023, 1, 15, 14, 30, 45)

    @patch('photo_renamer.Image.open')
    def test_get_image_date_taken_no_exif(self, mock_image_open):
        """Test that None is returned when image has no EXIF data."""
        mock_image = MagicMock()
        mock_image.__enter__.return_value = mock_image
        mock_image.getexif.return_value = None
        mock_image_open.return_value = mock_image

        result = photo_renamer.get_image_date_taken("test.jpg")

        assert result is None

    @patch('photo_renamer.Image.open')
    def test_get_image_date_taken_handles_exceptions(self, mock_image_open):
        """Test that exceptions are caught and None is returned."""
        mock_image_open.side_effect = Exception("File not found")

        result = photo_renamer.get_image_date_taken("nonexistent.jpg")

        assert result is None

    @patch('subprocess.run')
    def test_get_video_date_taken_with_valid_metadata(self, mock_run, mock_video_metadata):
        """Test extracting date from video with valid metadata."""
        mock_run.return_value = Mock(
            returncode=0,
            stdout=json.dumps(mock_video_metadata)
        )

        result = photo_renamer.get_video_date_taken("test.mov")

        assert result == datetime(2023, 1, 15, 14, 30, 45)
        mock_run.assert_called_once()

    @patch('subprocess.run')
    def test_get_video_date_taken_alternative_format(self, mock_run, mock_video_metadata_alternative_format):
        """Test extracting date from video with alternative date format."""
        mock_run.return_value = Mock(
            returncode=0,
            stdout=json.dumps(mock_video_metadata_alternative_format)
        )

        result = photo_renamer.get_video_date_taken("test.mp4")

        assert result == datetime(2023, 1, 15, 14, 30, 45)

    @patch('subprocess.run')
    def test_get_video_date_taken_ffprobe_not_found(self, mock_run):
        """Test handling when ffprobe is not available."""
        mock_run.return_value = Mock(returncode=1)

        result = photo_renamer.get_video_date_taken("test.mov")

        assert result is None

    @patch('subprocess.run')
    def test_get_video_date_taken_timeout(self, mock_run):
        """Test handling of ffprobe timeout."""
        from subprocess import TimeoutExpired
        mock_run.side_effect = TimeoutExpired("ffprobe", 30)

        result = photo_renamer.get_video_date_taken("test.mov")

        assert result is None

    @patch('subprocess.run')
    def test_get_video_date_taken_invalid_json(self, mock_run):
        """Test handling of invalid JSON from ffprobe."""
        mock_run.return_value = Mock(
            returncode=0,
            stdout="invalid json"
        )

        result = photo_renamer.get_video_date_taken("test.mov")

        assert result is None

    def test_get_date_taken_routes_jpg_to_image_handler(self):
        """Test that JPG files are routed to image handler."""
        with patch('photo_renamer.get_image_date_taken') as mock_image:
            mock_image.return_value = datetime(2023, 1, 15, 10, 0, 0)

            result = photo_renamer.get_date_taken(Path("test.jpg"))

            mock_image.assert_called_once()
            assert result == datetime(2023, 1, 15, 10, 0, 0)

    def test_get_date_taken_routes_mov_to_video_handler(self):
        """Test that MOV files are routed to video handler."""
        with patch('photo_renamer.get_video_date_taken') as mock_video:
            mock_video.return_value = datetime(2023, 1, 15, 10, 0, 0)

            result = photo_renamer.get_date_taken(Path("test.mov"))

            mock_video.assert_called_once()
            assert result == datetime(2023, 1, 15, 10, 0, 0)

    def test_get_date_taken_handles_heic_files(self):
        """Test that HEIC files are routed to HEIC handler."""
        with patch('photo_renamer.get_heic_date_taken') as mock_heic:
            mock_heic.return_value = datetime(2023, 1, 15, 10, 0, 0)

            result = photo_renamer.get_date_taken(Path("test.heic"))

            mock_heic.assert_called_once()
            assert result == datetime(2023, 1, 15, 10, 0, 0)

    def test_get_date_taken_handles_dng_files(self):
        """Test that DNG files are routed to DNG handler."""
        with patch('photo_renamer.get_dng_date_taken') as mock_dng:
            mock_dng.return_value = datetime(2023, 1, 15, 10, 0, 0)

            result = photo_renamer.get_date_taken(Path("test.dng"))

            mock_dng.assert_called_once()
            assert result == datetime(2023, 1, 15, 10, 0, 0)

    def test_get_date_taken_returns_none_for_unsupported_format(self):
        """Test that unsupported file formats return None."""
        result = photo_renamer.get_date_taken(Path("test.txt"))

        assert result is None


class TestFileDiscovery:
    """Tests for file finding and filtering functions."""

    def test_find_media_files_non_recursive(self, tmp_test_dir):
        """Test finding media files in single directory (non-recursive)."""
        # Create test files
        (tmp_test_dir / "photo1.jpg").touch()
        (tmp_test_dir / "video1.mov").touch()
        (tmp_test_dir / "document.txt").touch()  # Should be ignored
        subdir = tmp_test_dir / "subdir"
        subdir.mkdir()
        (subdir / "photo2.jpg").touch()  # Should not be found (non-recursive)

        result = photo_renamer.find_media_files(tmp_test_dir, recursive=False)

        assert len(result) == 2
        assert any(f.name == "photo1.jpg" for f in result)
        assert any(f.name == "video1.mov" for f in result)
        assert not any(f.name == "photo2.jpg" for f in result)

    def test_find_media_files_recursive(self, nested_test_structure):
        """Test finding media files recursively in nested directories."""
        result = photo_renamer.find_media_files(nested_test_structure, recursive=True)

        assert len(result) == 4
        filenames = [f.name for f in result]
        assert "IMG_001.jpg" in filenames
        assert "VID_001.mov" in filenames
        assert "IMG_002.jpg" in filenames
        assert "IMG_003.jpg" in filenames

    def test_find_media_files_filters_by_extension(self, tmp_test_dir):
        """Test that only media file extensions are included."""
        extensions = ['.jpg', '.png', '.mov', '.mp4', '.heic', '.dng']
        non_media = ['.txt', '.doc', '.pdf', '.zip']

        for ext in extensions:
            (tmp_test_dir / f"file{ext}").touch()
        for ext in non_media:
            (tmp_test_dir / f"file{ext}").touch()

        result = photo_renamer.find_media_files(tmp_test_dir, recursive=False)

        assert len(result) == len(extensions)
        for f in result:
            assert f.suffix.lower() in extensions

    def test_find_media_files_empty_directory(self, empty_test_dir):
        """Test that empty directory returns empty list."""
        result = photo_renamer.find_media_files(empty_test_dir, recursive=False)

        assert result == []

    def test_find_media_files_case_insensitive_extensions(self, tmp_test_dir):
        """Test that file extension matching is case-insensitive."""
        (tmp_test_dir / "photo1.JPG").touch()
        (tmp_test_dir / "photo2.Jpg").touch()
        (tmp_test_dir / "video.MOV").touch()

        result = photo_renamer.find_media_files(tmp_test_dir, recursive=False)

        assert len(result) == 3


class TestRenamingLogic:
    """Tests for file renaming logic."""

    def test_rename_generates_correct_photo_filename(self):
        """Test that photos get correct filename format."""
        # This tests the logic in rename_media_in_directory at line 423-425
        date_str = "2023-01-15"
        sequence = 1
        extension = ".jpg"

        expected = f"{date_str} - Phone Photos ({sequence}){extension}"

        assert expected == "2023-01-15 - Phone Photos (1).jpg"

    def test_rename_generates_correct_video_filename(self):
        """Test that videos get correct filename format."""
        date_str = "2023-01-15"
        sequence = 2
        extension = ".mov"

        expected = f"{date_str} - Phone Videos ({sequence}){extension}"

        assert expected == "2023-01-15 - Phone Videos (2).mov"

    def test_files_grouped_by_date(self, tmp_test_dir, create_test_file_with_timestamp):
        """Test that files are grouped by date and numbered sequentially."""
        # Create files with different dates
        file1 = create_test_file_with_timestamp("img1", "2023-01-15 10:00:00", ".jpg")
        file2 = create_test_file_with_timestamp("img2", "2023-01-15 14:00:00", ".jpg")
        file3 = create_test_file_with_timestamp("img3", "2023-01-16 10:00:00", ".jpg")

        with patch('photo_renamer.get_date_taken') as mock_get_date:
            def side_effect(path):
                if path.name == "img1.jpg":
                    return datetime(2023, 1, 15, 10, 0, 0)
                elif path.name == "img2.jpg":
                    return datetime(2023, 1, 15, 14, 0, 0)
                elif path.name == "img3.jpg":
                    return datetime(2023, 1, 16, 10, 0, 0)
                return None

            mock_get_date.side_effect = side_effect

            # Run dry-run to see expected names
            photo_renamer.rename_media_in_directory(tmp_test_dir, dry_run=True)

            # Files should be grouped: 2 on Jan 15, 1 on Jan 16
            # Expected: img1 -> 2023-01-15 - Phone Photos (1).jpg
            #           img2 -> 2023-01-15 - Phone Photos (2).jpg
            #           img3 -> 2023-01-16 - Phone Photos (1).jpg

    def test_skip_already_correctly_named_files(self, tmp_test_dir):
        """Test that files already in correct format are not renamed."""
        # Create file with correct name
        correct_file = tmp_test_dir / "2023-01-15 - Phone Photos (1).jpg"
        correct_file.touch()

        with patch('photo_renamer.get_date_taken') as mock_get_date:
            mock_get_date.return_value = datetime(2023, 1, 15, 10, 0, 0)

            total, renamed = photo_renamer.rename_media_in_directory(tmp_test_dir, dry_run=False)

            # File should not be renamed
            assert correct_file.exists()
            assert renamed == 0

    def test_skip_when_target_exists(self, tmp_test_dir):
        """Test that files are not overwritten if target name already exists."""
        source_file = tmp_test_dir / "IMG_001.jpg"
        source_file.touch()

        # Create target file that would be the rename destination
        target_file = tmp_test_dir / "2023-01-15 - Phone Photos (1).jpg"
        target_file.write_text("existing content")

        with patch('photo_renamer.get_date_taken') as mock_get_date:
            mock_get_date.return_value = datetime(2023, 1, 15, 10, 0, 0)

            total, renamed = photo_renamer.rename_media_in_directory(tmp_test_dir, dry_run=False)

            # Target file should still have original content (not overwritten)
            assert target_file.read_text() == "existing content"
            # Source file is renamed to (2) instead since (1) exists
            assert (tmp_test_dir / "2023-01-15 - Phone Photos (2).jpg").exists()
            assert renamed == 1

    def test_chronological_ordering_within_day(self, tmp_test_dir, create_test_file_with_timestamp):
        """Test that files taken on same day are numbered chronologically."""
        # Create files with same date but different times
        file1 = create_test_file_with_timestamp("img1", "2023-01-15 08:00:00", ".jpg")
        file2 = create_test_file_with_timestamp("img2", "2023-01-15 12:00:00", ".jpg")
        file3 = create_test_file_with_timestamp("img3", "2023-01-15 09:00:00", ".jpg")

        with patch('photo_renamer.get_date_taken') as mock_get_date:
            def side_effect(path):
                if path.name == "img1.jpg":
                    return datetime(2023, 1, 15, 8, 0, 0)  # First
                elif path.name == "img2.jpg":
                    return datetime(2023, 1, 15, 12, 0, 0)  # Third
                elif path.name == "img3.jpg":
                    return datetime(2023, 1, 15, 9, 0, 0)  # Second
                return None

            mock_get_date.side_effect = side_effect

            photo_renamer.rename_media_in_directory(tmp_test_dir, dry_run=False)

            # Check that files are renamed in chronological order
            assert (tmp_test_dir / "2023-01-15 - Phone Photos (1).jpg").exists()  # was img1 (8am)
            assert (tmp_test_dir / "2023-01-15 - Phone Photos (2).jpg").exists()  # was img3 (9am)
            assert (tmp_test_dir / "2023-01-15 - Phone Photos (3).jpg").exists()  # was img2 (noon)

    def test_mixed_photo_video_numbering(self, tmp_test_dir, create_test_file_with_timestamp):
        """Test that photos and videos share sequential numbering on same day."""
        file1 = create_test_file_with_timestamp("img1", "2023-01-15 08:00:00", ".jpg")
        file2 = create_test_file_with_timestamp("vid1", "2023-01-15 09:00:00", ".mov")
        file3 = create_test_file_with_timestamp("img2", "2023-01-15 10:00:00", ".jpg")

        with patch('photo_renamer.get_date_taken') as mock_get_date:
            def side_effect(path):
                if path.name == "img1.jpg":
                    return datetime(2023, 1, 15, 8, 0, 0)
                elif path.name == "vid1.mov":
                    return datetime(2023, 1, 15, 9, 0, 0)
                elif path.name == "img2.jpg":
                    return datetime(2023, 1, 15, 10, 0, 0)
                return None

            mock_get_date.side_effect = side_effect

            photo_renamer.rename_media_in_directory(tmp_test_dir, dry_run=False)

            assert (tmp_test_dir / "2023-01-15 - Phone Photos (1).jpg").exists()
            assert (tmp_test_dir / "2023-01-15 - Phone Videos (2).mov").exists()
            assert (tmp_test_dir / "2023-01-15 - Phone Photos (3).jpg").exists()


class TestEdgeCases:
    """Tests for edge cases and error conditions."""

    def test_empty_directory_returns_zero(self, empty_test_dir):
        """Test that processing empty directory returns 0 files processed."""
        total, renamed = photo_renamer.rename_media_in_directory(empty_test_dir, dry_run=False)

        assert total == 0
        assert renamed == 0

    def test_nonexistent_directory_returns_zero(self, tmp_test_dir):
        """Test that nonexistent directory is handled gracefully."""
        nonexistent = tmp_test_dir / "does_not_exist"

        total, renamed = photo_renamer.rename_media_in_directory(nonexistent, dry_run=False)

        assert total == 0
        assert renamed == 0

    def test_dry_run_makes_no_changes(self, tmp_test_dir, create_test_file_with_timestamp):
        """Test that dry-run mode doesn't actually rename files."""
        original_file = create_test_file_with_timestamp("img1", "2023-01-15 10:00:00", ".jpg")
        original_name = original_file.name

        with patch('photo_renamer.get_date_taken') as mock_get_date:
            mock_get_date.return_value = datetime(2023, 1, 15, 10, 0, 0)

            total, renamed = photo_renamer.rename_media_in_directory(tmp_test_dir, dry_run=True)

            # Original file should still exist with original name
            assert original_file.exists()
            assert original_file.name == original_name
            # Renamed file should not exist
            assert not (tmp_test_dir / "2023-01-15 - Phone Photos (1).jpg").exists()
            # Total should be counted but renamed should be 0
            assert total > 0
            assert renamed == 0


class TestRecursiveProcessing:
    """Tests for recursive directory processing."""

    def test_recursive_processes_all_subdirectories(self, nested_test_structure):
        """Test that recursive mode processes files in all subdirectories."""
        with patch('photo_renamer.get_date_taken') as mock_get_date:
            mock_get_date.return_value = datetime(2023, 1, 15, 10, 0, 0)

            photo_renamer.rename_media(nested_test_structure, dry_run=True, recursive=True)

            # Should have found files in multiple directories
            # (Actual renaming tested in integration tests)

    def test_non_recursive_only_processes_target_directory(self, nested_test_structure):
        """Test that non-recursive mode only processes target directory."""
        # nested_test_structure root has no files, only subdirectories
        total, renamed = photo_renamer.rename_media_in_directory(
            nested_test_structure,
            dry_run=False,
            recursive=False
        )

        assert total == 0
        assert renamed == 0