# Phone Media File Renamer

A Python script that renames media files (photos and videos) based on their "Date taken" metadata from EXIF data and video metadata.

## Features

- Renames photos to format: `yyyy-mm-dd - Phone Photos (N).ext`
- Renames videos to format: `yyyy-mm-dd - Phone Videos (N).ext`
- Uses actual "Date taken" from EXIF metadata (photos) and video metadata (videos)
- Groups files by date with sequential numbering
- Supports dry-run mode to preview changes
- **Recursive processing**: Process all subdirectories
- Falls back to file creation date if metadata is missing
- **Image formats**: JPG, PNG, TIFF, BMP
- **Video formats**: MOV, MP4, AVI, MKV, M4V, 3GP, WMV

## Installation

1. Install Python dependencies:
```bash
pip install -r requirements.txt
```

2. **(Optional)** Install FFmpeg for video metadata extraction:
   - **Windows**: `winget install --id=Gyan.FFmpeg`
   - **macOS**: `brew install ffmpeg`
   - **Linux**: `sudo apt install ffmpeg` (Ubuntu/Debian) or equivalent

   *Note: Without FFmpeg, video files will still be renamed using file creation dates*

## Usage

### Basic usage (rename files in current directory):
```bash
python photo_renamer.py
```

### Specify a directory:
```bash
python photo_renamer.py /path/to/media
python photo_renamer.py TestPhotos
```

### Dry run (preview changes without renaming):
```bash
python photo_renamer.py --dry-run
python photo_renamer.py TestPhotos --dry-run
```

### Recursive processing (process all subdirectories):
```bash
python photo_renamer.py /path/to/media --recursive
python photo_renamer.py TestPhotos --recursive --dry-run
```

### Help:
```bash
python photo_renamer.py --help
```

## Example Output

The program will rename files like:

### Photos:
- `IMG_1234.jpg` → `2023-01-15 - Phone Photos (1).jpg`
- `IMG_1235.jpg` → `2023-01-15 - Phone Photos (2).jpg`
- `IMG_1236.jpg` → `2023-01-16 - Phone Photos (1).jpg`

### Videos:
- `IMG_1237.mov` → `2023-01-15 - Phone Videos (3).mov`
- `VID_1238.mp4` → `2023-01-15 - Phone Videos (4).mp4`

Files taken on the same day are numbered sequentially in chronological order, with photos and videos sharing the same numbering sequence.

### Recursive Mode
When using `--recursive`, the program processes each subdirectory separately:
```
Media/
├── 2023/
│   ├── IMG_001.jpg → 2023-01-15 - Phone Photos (1).jpg
│   ├── VID_001.mov → 2023-01-15 - Phone Videos (2).mov
│   └── IMG_002.jpg → 2023-01-15 - Phone Photos (3).jpg
└── 2024/
    ├── IMG_003.jpg → 2024-02-10 - Phone Photos (1).jpg
    └── VID_002.mp4 → 2024-02-10 - Phone Videos (2).mp4
```

## Safety Features

- **Dry run mode**: Always test with `--dry-run` first
- **Duplicate protection**: Won't overwrite existing files
- **Error handling**: Continues processing if individual files fail
- **Metadata fallback**: Uses file creation date if metadata is missing
- **FFmpeg optional**: Works without FFmpeg (uses file dates for videos)

## Video Metadata Support

The program extracts "creation time" from video metadata using FFmpeg's `ffprobe`. Supported metadata fields:
- `creation_time` (most common)
- `date`
- `creation_date`
- `com.apple.quicktime.creationdate` (QuickTime)

Without FFmpeg installed, videos will be renamed using file creation dates, which may be less accurate than the original recording date.

## Dependencies

This project relies on several open source libraries and packages:

### Required Python Packages
- **[Pillow](https://pillow.readthedocs.io/)** (`>=10.0.0`) - Python Imaging Library for JPEG, PNG, TIFF, and BMP image processing and EXIF metadata extraction
  - License: Historical Permission Notice and Disclaimer (HPND)
  - Used for: Reading EXIF metadata from standard image formats

### Optional Python Packages
- **[pillow-heif](https://github.com/bigcat88/pillow_heif)** - HEIF/HEIC image format support for Pillow
  - License: BSD-3-Clause
  - Used for: Reading EXIF metadata from HEIC/HEIF files (Apple photos)
  - Install: `pip install pillow-heif`

- **[ExifRead](https://github.com/ianare/exif-py)** - Pure Python library for extracting EXIF metadata
  - License: BSD-3-Clause
  - Used for: Reading EXIF metadata from DNG (Digital Negative) RAW files
  - Install: `pip install ExifRead`

### External Tools
- **[FFmpeg](https://ffmpeg.org/)** - Multimedia framework for video processing
  - License: GNU Lesser General Public License (LGPL) version 2.1+
  - Used for: Extracting creation time metadata from video files
  - Install: `winget install --id=Gyan.FFmpeg` (Windows)

### Built-in Python Libraries
- **argparse** - Command-line argument parsing
- **os** - Operating system interface
- **sys** - System-specific parameters and functions
- **json** - JSON encoder and decoder
- **subprocess** - Subprocess management
- **pathlib** - Object-oriented filesystem paths
- **datetime** - Date and time handling
- **collections** - Specialized container datatypes

All external dependencies are optional and the script will gracefully degrade functionality when they are not available, falling back to file system timestamps for date information.

## Testing

This project includes a comprehensive test suite with both unit tests and integration tests.

### Running Tests

```bash
# Install testing dependencies
pip install -r requirements.txt

# Run all tests
pytest

# Run with verbose output
pytest -v

# Run with code coverage report
pytest --cov=photo_renamer --cov-report=term-missing

# Run only unit tests (fast, uses mocks)
pytest test_photo_renamer.py

# Run only integration tests (uses real test files)
pytest test_integration.py

# Run a specific test class
pytest test_integration.py::TestRealFileMetadataExtraction -v
```

### Test Organization

The test suite is organized into three main files:

#### `conftest.py`
Contains pytest fixtures and test helpers:
- Temporary directory fixtures for safe file operations
- Mock EXIF and video metadata structures
- Factory fixtures for creating test files with specific timestamps
- Real test file fixtures that copy from the `TestFiles/` directory

#### `test_photo_renamer.py` - Unit Tests (32 tests)
Mock-based tests for fast, isolated testing:
- **Date Extraction Tests** - EXIF reading, video metadata parsing, fallback logic
- **File Discovery Tests** - Finding media files, extension filtering, recursive search
- **Renaming Logic Tests** - Filename generation, sequential numbering, collision handling
- **Edge Cases Tests** - Empty directories, nonexistent paths, dry-run mode
- **Recursive Processing Tests** - Nested directory handling

#### `test_integration.py` - Integration Tests (14 tests)
Tests using real media files from the `TestFiles/` directory:
- **Real File Metadata Extraction** - Validates EXIF and video metadata reading on actual files
- **Real File Renaming** - Tests actual file operations in safe temporary directories
- **Real World Scenarios** - Simulates typical usage patterns like processing phone exports

### Test Coverage

The test suite provides **63% code coverage** of the main script, covering:
- All major metadata extraction paths
- File discovery and filtering logic
- Renaming logic and collision handling
- Chronological ordering
- Recursive directory processing
- Dry-run mode
- Edge cases and error conditions

### Testing Dependencies

- **pytest** (`>=7.4.0`) - Test framework
- **pytest-cov** (`>=4.1.0`) - Code coverage reporting
- **pytest-mock** (`>=3.11.1`) - Mocking support

These are automatically installed when you run `pip install -r requirements.txt`.