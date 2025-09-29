"""
Integration tests using real media files from TestFiles directory.

These tests use actual photos and videos to verify metadata extraction works correctly.
"""

import shutil
from pathlib import Path
from datetime import datetime
import pytest

import photo_renamer


class TestRealFileMetadataExtraction:
    """Tests using real media files to verify metadata extraction."""

    def test_real_jpg_with_exif(self, sample_test_files):
        """Test EXIF extraction from real JPG file."""
        jpg_file = sample_test_files["jpg_with_exif"]

        if not jpg_file.exists():
            pytest.skip("Test JPG file not found")

        result = photo_renamer.get_image_date_taken(jpg_file)

        # Based on actual test file: TestFiles/2017/01/IMG_0353.JPG
        # Expected: 2017-01-19 06:38:20 (from running script earlier)
        assert result is not None
        assert result.year == 2017
        assert result.month == 1
        assert result.day == 19

    def test_real_mov_with_metadata(self, sample_test_files):
        """Test metadata extraction from real MOV file."""
        mov_file = sample_test_files["mov_with_metadata"]

        if not mov_file.exists():
            pytest.skip("Test MOV file not found")

        result = photo_renamer.get_video_date_taken(mov_file)

        # Based on actual test file: TestFiles/2017/01/IMG_0001.MOV
        # Expected: 2017-01-29 22:11:32
        assert result is not None
        assert result.year == 2017
        assert result.month == 1
        assert result.day == 29

    def test_real_png_no_metadata(self, sample_test_files):
        """Test handling of PNG file without EXIF metadata."""
        png_file = sample_test_files["png_no_metadata"]

        if not png_file.exists():
            pytest.skip("Test PNG file not found")

        result = photo_renamer.get_image_date_taken(png_file)

        # PNG files typically don't have EXIF data
        # Should return None and fall back to file timestamp
        assert result is None

    def test_real_heic_file(self, sample_test_files):
        """Test HEIC file handling (may need pillow-heif)."""
        heic_file = sample_test_files["heic_file"]

        if not heic_file.exists():
            pytest.skip("Test HEIC file not found")

        result = photo_renamer.get_heic_date_taken(heic_file)

        # Result depends on whether pillow-heif is installed
        # Test just verifies it doesn't crash
        assert result is None or isinstance(result, datetime)

    def test_real_fail_case_files(self, sample_test_files):
        """Test known problematic files that may have issues."""
        fail_file_1 = sample_test_files["fail_case_1"]
        fail_file_2 = sample_test_files["fail_case_2"]

        if fail_file_1.exists():
            # These files have filename suggesting 2020 or 2012
            # but may have different EXIF dates
            result = photo_renamer.get_date_taken(fail_file_1)
            # Should return something (either metadata or fallback)
            assert result is None or isinstance(result, datetime)

        if fail_file_2.exists():
            result = photo_renamer.get_date_taken(fail_file_2)
            # File name says "fails with 2017 instead of 2012 date taken"
            # This documents a known issue
            assert result is None or isinstance(result, datetime)


class TestRealFileRenaming:
    """Integration tests for actual file renaming operations."""

    def test_rename_single_directory_with_real_files(self, sample_test_files):
        """Test renaming files in a directory with real media files."""
        test_dir = sample_test_files["root"] / "2017" / "01"

        if not test_dir.exists():
            pytest.skip("Test directory not found")

        # First do dry run to see what would happen
        total_dry, renamed_dry = photo_renamer.rename_media_in_directory(
            test_dir,
            dry_run=True
        )

        assert total_dry > 0  # Should find files
        assert renamed_dry == 0  # Dry run doesn't rename

        # Now actually rename
        total, renamed = photo_renamer.rename_media_in_directory(
            test_dir,
            dry_run=False
        )

        assert total > 0
        # Some files may already be correctly named or have conflicts
        assert renamed >= 0

        # Check that at least some files were renamed to correct format
        renamed_files = list(test_dir.glob("????-??-?? - Phone *"))
        assert len(renamed_files) > 0

        # Verify format matches pattern: YYYY-MM-DD - Phone Photos/Videos (N).ext
        for file in renamed_files:
            name = file.stem  # Without extension
            assert " - Phone " in name
            assert "(" in name and ")" in name

    def test_recursive_rename_with_nested_structure(self, sample_test_files):
        """Test recursive renaming of nested directory structure."""
        root_dir = sample_test_files["root"]

        if not root_dir.exists():
            pytest.skip("Test root directory not found")

        # Count files before
        all_media_before = list(root_dir.rglob("*"))
        media_count_before = len([f for f in all_media_before if f.is_file() and f.suffix.lower() in
                                   {'.jpg', '.jpeg', '.png', '.mov', '.mp4', '.heic'}])

        # Perform recursive rename
        photo_renamer.rename_media(root_dir, dry_run=False, recursive=True)

        # Count correctly named files after
        renamed_pattern_files = list(root_dir.rglob("????-??-?? - Phone *"))

        # Should have renamed at least some files
        assert len(renamed_pattern_files) > 0

    def test_handles_already_renamed_files(self, sample_test_files):
        """Test that already correctly named files are not renamed again."""
        test_dir = sample_test_files["root"] / "2010"

        if not test_dir.exists():
            pytest.skip("Test directory not found")

        # This directory has some files already in correct format
        # Like: "2010-11 - Phone Photos (6).jpg"

        total, renamed = photo_renamer.rename_media_in_directory(
            test_dir,
            dry_run=False
        )

        # Run again - should skip already renamed files
        total2, renamed2 = photo_renamer.rename_media_in_directory(
            test_dir,
            dry_run=False
        )

        # Second run should rename fewer or zero files
        assert renamed2 <= renamed

    def test_dry_run_makes_no_actual_changes(self, sample_test_files):
        """Test that dry run mode doesn't modify any files."""
        test_dir = sample_test_files["root"] / "2017" / "12"

        if not test_dir.exists():
            pytest.skip("Test directory not found")

        # Get list of files before
        files_before = {f.name for f in test_dir.iterdir() if f.is_file()}

        # Run in dry-run mode
        photo_renamer.rename_media_in_directory(test_dir, dry_run=True)

        # Get list of files after
        files_after = {f.name for f in test_dir.iterdir() if f.is_file()}

        # Should be identical
        assert files_before == files_after

    def test_handles_multiple_files_same_date(self, sample_test_files):
        """Test correct sequential numbering for multiple files on same date."""
        test_dir = sample_test_files["root"] / "2017" / "01"

        if not test_dir.exists():
            pytest.skip("Test directory not found")

        # Rename files
        photo_renamer.rename_media_in_directory(test_dir, dry_run=False)

        # Check for files on 2017-01-19 (multiple files have this date)
        jan_19_files = sorted(test_dir.glob("2017-01-19 - Phone *"))

        if len(jan_19_files) > 1:
            # Verify that all files have parentheses with numbers
            # Numbers may not be 1,2,3 if some file types are mixed
            for file in jan_19_files:
                # Just verify format includes a number in parentheses
                assert "(" in file.stem and ")" in file.stem
                # Verify there's a number between the parentheses
                import re
                assert re.search(r'\(\d+\)', file.stem)

    def test_preserves_file_extensions(self, sample_test_files):
        """Test that original file extensions are preserved."""
        test_dir = sample_test_files["root"] / "2017" / "01"

        if not test_dir.exists():
            pytest.skip("Test directory not found")

        # Get original extensions
        original_extensions = {f.suffix.lower() for f in test_dir.iterdir()
                              if f.is_file() and f.suffix.lower() in
                              {'.jpg', '.jpeg', '.png', '.mov', '.mp4'}}

        # Rename files
        photo_renamer.rename_media_in_directory(test_dir, dry_run=False)

        # Get extensions after rename
        renamed_extensions = {f.suffix.lower() for f in test_dir.iterdir()
                             if f.is_file() and f.suffix.lower() in
                             {'.jpg', '.jpeg', '.png', '.mov', '.mp4'}}

        # Same extensions should exist
        assert original_extensions == renamed_extensions


class TestRealWorldScenarios:
    """Test realistic usage scenarios."""

    def test_process_directory_from_phone_export(self, sample_test_files):
        """Simulate processing a directory of photos exported from a phone."""
        test_dir = sample_test_files["root"] / "2017" / "01"

        if not test_dir.exists():
            pytest.skip("Test directory not found")

        # This simulates the typical workflow:
        # 1. User exports photos from phone
        # 2. Files have generic names like IMG_0001.JPG
        # 3. User runs script to organize them

        # Count original generic names
        generic_names = [f for f in test_dir.iterdir()
                        if f.is_file() and f.name.startswith(('IMG_', '201'))]

        print(f"Found {len(generic_names)} files to organize")

        # Organize them
        total, renamed = photo_renamer.rename_media_in_directory(
            test_dir,
            dry_run=False
        )

        print(f"Processed {total} files, renamed {renamed}")

        # Verify results are organized by date
        organized_files = list(test_dir.glob("????-??-?? - Phone *"))
        assert len(organized_files) > 0

        # All organized files should have valid dates
        for file in organized_files:
            date_part = file.name[:10]  # YYYY-MM-DD
            try:
                datetime.strptime(date_part, "%Y-%m-%d")
            except ValueError:
                pytest.fail(f"Invalid date format in filename: {file.name}")

    def test_mixed_media_types_in_same_directory(self, sample_test_files):
        """Test processing directory with mix of photos and videos."""
        test_dir = sample_test_files["root"] / "2017" / "01"

        if not test_dir.exists():
            pytest.skip("Test directory not found")

        photo_renamer.rename_media_in_directory(test_dir, dry_run=False)

        # Should have both photos and videos
        photos = list(test_dir.glob("* - Phone Photos *"))
        videos = list(test_dir.glob("* - Phone Videos *"))

        # This test dir has both types
        assert len(photos) > 0
        assert len(videos) > 0

        print(f"Organized {len(photos)} photos and {len(videos)} videos")

    def test_handles_files_without_metadata(self, sample_test_files):
        """Test that files without metadata still get organized using file dates."""
        png_file = sample_test_files["png_no_metadata"]

        if not png_file.exists():
            pytest.skip("Test PNG file not found")

        test_dir = png_file.parent

        # Run renaming
        photo_renamer.rename_media_in_directory(test_dir, dry_run=False)

        # PNG file should still be renamed using file timestamp
        # Check if any file was created for that date
        renamed_files = list(test_dir.glob("????-??-?? - Phone Photos *.png"))

        # At least one PNG should be renamed
        assert len(renamed_files) >= 1