#!/usr/bin/env python3
"""
Phone Media File Renamer

This script renames photos and videos in a directory based on their "Date taken" metadata.
The new filename format is: yyyy-mm-dd - Phone Photos (N).ext
where N is a sequential number for files taken on the same day.
"""

import os
import sys
import json
import subprocess
from pathlib import Path
from datetime import datetime
from collections import defaultdict
import argparse

try:
    from PIL import Image
    from PIL.ExifTags import TAGS
except ImportError:
    print("Error: Pillow library is required. Install it with: pip install Pillow")
    sys.exit(1)


def get_video_date_taken(video_path):
    """
    Extract the 'Date taken' from video metadata using ffprobe.

    Args:
        video_path (str): Path to the video file

    Returns:
        datetime or None: Date taken if found, None otherwise
    """
    try:
        # Use ffprobe to extract metadata
        cmd = [
            'ffprobe',
            '-v', 'quiet',
            '-print_format', 'json',
            '-show_format',
            '-show_streams',
            str(video_path)
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

        if result.returncode != 0:
            return None

        metadata = json.loads(result.stdout)

        # Look for creation_time in format section
        if 'format' in metadata and 'tags' in metadata['format']:
            tags = metadata['format']['tags']

            # Try different possible date field names
            date_fields = ['creation_time', 'date', 'creation_date', 'com.apple.quicktime.creationdate']

            for field in date_fields:
                if field in tags:
                    date_str = tags[field]
                    # Parse ISO format: "2023-01-15T14:30:45.000000Z"
                    try:
                        # Handle different datetime formats
                        if 'T' in date_str:
                            # ISO format
                            date_str = date_str.replace('Z', '+00:00')
                            if '.' in date_str:
                                return datetime.fromisoformat(date_str.split('.')[0])
                            else:
                                return datetime.fromisoformat(date_str.replace('+00:00', ''))
                        else:
                            # Try other common formats
                            for fmt in ['%Y-%m-%d %H:%M:%S', '%Y:%m:%d %H:%M:%S']:
                                try:
                                    return datetime.strptime(date_str, fmt)
                                except ValueError:
                                    continue
                    except (ValueError, TypeError):
                        continue

        # Also check streams for metadata
        if 'streams' in metadata:
            for stream in metadata['streams']:
                if 'tags' in stream:
                    tags = stream['tags']
                    for field in ['creation_time', 'date']:
                        if field in tags:
                            date_str = tags[field]
                            try:
                                if 'T' in date_str:
                                    date_str = date_str.replace('Z', '+00:00')
                                    if '.' in date_str:
                                        return datetime.fromisoformat(date_str.split('.')[0])
                                    else:
                                        return datetime.fromisoformat(date_str.replace('+00:00', ''))
                            except (ValueError, TypeError):
                                continue

    except subprocess.TimeoutExpired:
        print(f"Warning: ffprobe timeout for {video_path}")
    except subprocess.CalledProcessError:
        pass
    except json.JSONDecodeError:
        pass
    except Exception as e:
        print(f"Warning: Could not read video metadata from {video_path}: {e}")

    return None


def get_image_date_taken(image_path):
    """
    Extract the 'Date taken' from image EXIF data.

    Args:
        image_path (str): Path to the image file

    Returns:
        datetime or None: Date taken if found, None otherwise
    """
    try:
        with Image.open(image_path) as image:
            exifdata = image.getexif()

            if exifdata is not None:
                # First, check main EXIF data
                for tag_id in exifdata:
                    tag = TAGS.get(tag_id, tag_id)
                    value = exifdata.get(tag_id)

                    # Look for DateTime, DateTimeOriginal, or DateTimeDigitized
                    if tag in ['DateTime', 'DateTimeOriginal', 'DateTimeDigitized']:
                        try:
                            # Parse the datetime string (format: "YYYY:MM:DD HH:MM:SS")
                            return datetime.strptime(value, "%Y:%m:%d %H:%M:%S")
                        except (ValueError, TypeError):
                            continue

                # If not found in main EXIF, check EXIF IFD (used by some cameras like Nokia/Windows Phone)
                try:
                    if hasattr(exifdata, 'get_ifd'):
                        exif_ifd = exifdata.get_ifd(0x8769)  # ExifOffset IFD
                        for tag_id in exif_ifd:
                            tag = TAGS.get(tag_id, tag_id)
                            value = exif_ifd.get(tag_id)

                            # Look for DateTime, DateTimeOriginal, or DateTimeDigitized in IFD
                            if tag in ['DateTime', 'DateTimeOriginal', 'DateTimeDigitized']:
                                try:
                                    # Parse the datetime string (format: "YYYY:MM:DD HH:MM:SS")
                                    return datetime.strptime(value, "%Y:%m:%d %H:%M:%S")
                                except (ValueError, TypeError):
                                    continue
                except Exception:
                    # If EXIF IFD reading fails, continue without error
                    pass

    except Exception as e:
        print(f"Warning: Could not read EXIF data from {image_path}: {e}")

    return None


def get_heic_date_taken(image_path):
    """
    Extract the 'Date taken' from HEIC image metadata.

    Args:
        image_path (str): Path to the HEIC image file

    Returns:
        datetime or None: Date taken if found, None otherwise
    """
    try:
        # Try using pillow-heif if available
        try:
            from pillow_heif import register_heif_opener
            register_heif_opener()

            with Image.open(image_path) as image:
                exifdata = image.getexif()

                if exifdata is not None:
                    # First, check main EXIF data
                    for tag_id in exifdata:
                        tag = TAGS.get(tag_id, tag_id)
                        value = exifdata.get(tag_id)

                        # Look for DateTime, DateTimeOriginal, or DateTimeDigitized
                        if tag in ['DateTime', 'DateTimeOriginal', 'DateTimeDigitized']:
                            try:
                                # Parse the datetime string (format: "YYYY:MM:DD HH:MM:SS")
                                return datetime.strptime(value, "%Y:%m:%d %H:%M:%S")
                            except (ValueError, TypeError):
                                continue

                    # If not found in main EXIF, check EXIF IFD
                    try:
                        if hasattr(exifdata, 'get_ifd'):
                            exif_ifd = exifdata.get_ifd(0x8769)  # ExifOffset IFD
                            for tag_id in exif_ifd:
                                tag = TAGS.get(tag_id, tag_id)
                                value = exif_ifd.get(tag_id)

                                # Look for DateTime, DateTimeOriginal, or DateTimeDigitized in IFD
                                if tag in ['DateTime', 'DateTimeOriginal', 'DateTimeDigitized']:
                                    try:
                                        # Parse the datetime string (format: "YYYY:MM:DD HH:MM:SS")
                                        return datetime.strptime(value, "%Y:%m:%d %H:%M:%S")
                                    except (ValueError, TypeError):
                                        continue
                    except Exception:
                        # If EXIF IFD reading fails, continue without error
                        pass

        except ImportError:
            print(f"Warning: pillow-heif not available for HEIC processing. Install with: pip install pillow-heif")
            return None

    except Exception as e:
        print(f"Warning: Could not read HEIC metadata from {image_path}: {e}")

    return None


def get_dng_date_taken(image_path):
    """
    Extract the 'Date taken' from DNG (Digital Negative) image metadata.

    Args:
        image_path (str): Path to the DNG image file

    Returns:
        datetime or None: Date taken if found, None otherwise
    """
    try:
        # Try using exifread library for DNG files
        try:
            import exifread

            with open(image_path, 'rb') as f:
                tags = exifread.process_file(f)

                # Look for date/time tags in EXIF data
                date_tags = [
                    'EXIF DateTimeOriginal',
                    'EXIF DateTimeDigitized',
                    'Image DateTime'
                ]

                for tag_name in date_tags:
                    if tag_name in tags:
                        date_str = str(tags[tag_name])
                        try:
                            # Parse the datetime string (format: "YYYY:MM:DD HH:MM:SS")
                            return datetime.strptime(date_str, "%Y:%m:%d %H:%M:%S")
                        except (ValueError, TypeError):
                            continue

        except ImportError:
            print(f"Warning: exifread not available for DNG processing. Install with: pip install ExifRead")
            return None

    except Exception as e:
        print(f"Warning: Could not read DNG metadata from {image_path}: {e}")

    return None


def get_date_taken(file_path):
    """
    Extract the 'Date taken' from file metadata (images or videos).

    Args:
        file_path (Path): Path to the file

    Returns:
        datetime or None: Date taken if found, None otherwise
    """
    file_ext = file_path.suffix.lower()

    # Handle image files
    if file_ext in {'.jpg', '.jpeg', '.png', '.tiff', '.tif', '.bmp'}:
        return get_image_date_taken(file_path)

    # Handle DNG files
    elif file_ext == '.dng':
        return get_dng_date_taken(file_path)

    # Handle HEIC files
    elif file_ext in {'.heic', '.heif'}:
        return get_heic_date_taken(file_path)

    # Handle video files
    elif file_ext in {'.mov', '.mp4', '.avi', '.mkv', '.m4v', '.3gp', '.wmv'}:
        return get_video_date_taken(file_path)

    return None


def get_best_fallback_date(file_path):
    """
    Get the best available date as fallback when metadata is not available.
    Uses the earliest reasonable timestamp from file attributes.

    Args:
        file_path (str): Path to the file

    Returns:
        datetime: Best available date
    """
    stat = os.stat(file_path)

    # Get all available timestamps
    creation_time = datetime.fromtimestamp(stat.st_ctime)
    modified_time = datetime.fromtimestamp(stat.st_mtime)
    access_time = datetime.fromtimestamp(stat.st_atime)

    # If creation time is significantly newer than modified time,
    # the file was likely copied/moved, so use modified time instead
    if creation_time > modified_time:
        # Use modified time as it's likely closer to the original date
        return modified_time

    # Otherwise, use the earliest available timestamp
    return min(creation_time, modified_time, access_time)


def find_media_files(directory, recursive=False):
    """
    Find all image and video files in a directory, optionally recursively.

    Args:
        directory (Path): Directory to search
        recursive (bool): If True, search subdirectories recursively

    Returns:
        list: List of Path objects for media files
    """
    media_extensions = {
        # Image formats
        '.jpg', '.jpeg', '.png', '.tiff', '.tif', '.bmp', '.heic', '.heif', '.dng',
        # Video formats
        '.mov', '.mp4', '.avi', '.mkv', '.m4v', '.3gp', '.wmv'
    }
    media_files = []

    if recursive:
        for file_path in directory.rglob('*'):
            if file_path.is_file() and file_path.suffix.lower() in media_extensions:
                media_files.append(file_path)
    else:
        for file_path in directory.iterdir():
            if file_path.is_file() and file_path.suffix.lower() in media_extensions:
                media_files.append(file_path)

    return media_files


def rename_media_in_directory(directory_path, dry_run=False, recursive=False):
    """
    Rename photos and videos in a single directory.

    Args:
        directory_path (Path): Path to directory containing media files
        dry_run (bool): If True, only show what would be renamed without actually renaming
        recursive (bool): If True, process subdirectories recursively

    Returns:
        tuple: (total_files_processed, total_files_renamed)
    """
    directory = Path(directory_path)

    if not directory.exists():
        print(f"Error: Directory '{directory_path}' does not exist.")
        return 0, 0

    # Find all media files
    media_files = find_media_files(directory, recursive=False)

    if not media_files:
        print(f"No image or video files found in '{directory_path}'.")
        return 0, 0

    print(f"\nProcessing directory: {directory_path}")
    print(f"Found {len(media_files)} media files.")

    # Group files by date
    files_by_date = defaultdict(list)

    for file_path in media_files:
        print(f"Processing: {file_path.name}")

        # Try to get date from metadata first
        date_taken = get_date_taken(file_path)

        if date_taken is None:
            print(f"  No metadata date found, using best available file date")
            date_taken = get_best_fallback_date(file_path)
        else:
            print(f"  Found metadata date: {date_taken}")

        date_str = date_taken.strftime("%Y-%m-%d")
        files_by_date[date_str].append((file_path, date_taken))

    # Sort files within each date by time and rename
    total_renamed = 0

    for date_str, file_list in sorted(files_by_date.items()):
        # Sort by full datetime to maintain chronological order within the day
        file_list.sort(key=lambda x: x[1])

        print(f"\nProcessing {len(file_list)} files for date {date_str}:")

        for i, (file_path, _) in enumerate(file_list, 1):
            # Determine if it's a photo or video for naming
            file_ext = file_path.suffix.lower()
            if file_ext in {'.mov', '.mp4', '.avi', '.mkv', '.m4v', '.3gp', '.wmv'}:
                new_name = f"{date_str} - Phone Videos ({i}){file_ext}"
            else:
                new_name = f"{date_str} - Phone Photos ({i}){file_ext}"
            new_path = file_path.parent / new_name

            if file_path.name == new_name:
                print(f"  {file_path.name} -> (already correctly named)")
                continue

            if new_path.exists():
                print(f"  {file_path.name} -> {new_name} (SKIPPED - target exists)")
                continue

            if dry_run:
                print(f"  {file_path.name} -> {new_name} (DRY RUN)")
            else:
                try:
                    file_path.rename(new_path)
                    print(f"  {file_path.name} -> {new_name} (RENAMED)")
                    total_renamed += 1
                except Exception as e:
                    print(f"  {file_path.name} -> {new_name} (ERROR: {e})")

    total_files = sum(len(files) for files in files_by_date.values())
    if dry_run:
        print(f"\nDirectory '{directory_path}' dry run completed. {total_files} files would be processed.")
    else:
        print(f"\nDirectory '{directory_path}' renaming completed. {total_renamed} files were renamed.")

    return total_files, total_renamed


def rename_media(directory_path, dry_run=False, recursive=False):
    """
    Rename photos and videos in the specified directory, optionally recursively.

    Args:
        directory_path (str): Path to directory containing media files
        dry_run (bool): If True, only show what would be renamed without actually renaming
        recursive (bool): If True, process subdirectories recursively
    """
    root_directory = Path(directory_path)

    if not root_directory.exists():
        print(f"Error: Directory '{directory_path}' does not exist.")
        return

    if recursive:
        print(f"Processing directory '{directory_path}' and all subdirectories recursively...")

        # Find all directories that contain media files
        directories_with_media = set()
        media_files = find_media_files(root_directory, recursive=True)

        for media_file in media_files:
            directories_with_media.add(media_file.parent)

        if not directories_with_media:
            print(f"No image or video files found in '{directory_path}' or its subdirectories.")
            return

        print(f"Found media files in {len(directories_with_media)} directories.")

        total_files_all = 0
        total_renamed_all = 0

        # Process each directory separately
        for directory in sorted(directories_with_media):
            files_processed, files_renamed = rename_media_in_directory(directory, dry_run, recursive=False)
            total_files_all += files_processed
            total_renamed_all += files_renamed

        print(f"\n{'='*50}")
        if dry_run:
            print(f"TOTAL: {total_files_all} files would be processed across {len(directories_with_media)} directories.")
        else:
            print(f"TOTAL: {total_renamed_all} files were renamed across {len(directories_with_media)} directories.")
    else:
        rename_media_in_directory(directory_path, dry_run, recursive=False)


def main():
    """Main function to handle command line arguments and run the media renamer."""
    # Check if ffprobe is available for video processing
    try:
        subprocess.run(['ffprobe', '-version'], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("Warning: ffprobe not found. Video file processing will be limited.")
        print("To process video files, install FFmpeg: https://ffmpeg.org/download.html")
        print("Image files will still be processed normally.\n")

    parser = argparse.ArgumentParser(
        description="Rename photos and videos based on their metadata",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python photo_renamer.py /path/to/photos
  python photo_renamer.py . --dry-run
  python photo_renamer.py TestPhotos
  python photo_renamer.py /path/to/photos --recursive
  python photo_renamer.py . --recursive --dry-run
        """
    )

    parser.add_argument(
        'directory',
        nargs='?',
        default='.',
        help='Directory containing photos and videos to rename (default: current directory)'
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be renamed without actually renaming files'
    )

    parser.add_argument(
        '--recursive',
        action='store_true',
        help='Process all subdirectories recursively'
    )

    args = parser.parse_args()

    print("Phone Media File Renamer")
    print("=" * 40)
    print(f"Target directory: {os.path.abspath(args.directory)}")
    print(f"Mode: {'DRY RUN' if args.dry_run else 'RENAME FILES'}")
    print(f"Recursive: {'Yes' if args.recursive else 'No'}")
    print()

    if args.dry_run:
        print("DRY RUN MODE: No files will be actually renamed.")
        print()

    rename_media(args.directory, dry_run=args.dry_run, recursive=args.recursive)


if __name__ == "__main__":
    main()