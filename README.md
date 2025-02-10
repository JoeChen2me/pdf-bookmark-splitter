# PDF Bookmark Splitter

A Python utility to split PDF files based on their bookmark structure. This tool allows you to divide a PDF into multiple files according to its bookmarks, with the ability to control the splitting depth level.  

- English 
- [简体中文](https://github.com/JoeChen2me/pdf-bookmark-splitter/blob/main/readme_zh-CN.md)
 
## Features

- Split PDF files based on bookmark structure
- Control splitting depth (e.g., split only at chapter level, or include subchapters)
- Customizable output directory
- Preserves PDF content and formatting
- Handles nested bookmarks
- Automatically creates clean filenames from bookmark titles

## Requirements

- Python 3.6 or higher
- PyPDF2 library

## Installation

1. Ensure you have Python installed on your system
2. Install the required PyPDF2 library:
```bash
pip install PyPDF2
```

## Usage

Basic command format:
```bash
python split_pdf_by_bookmarks.py input_pdf [-o output_dir] [-d depth]
```

### Parameters

- `input_pdf` (required): Path to the input PDF file
- `-o, --output-dir`: Directory where split PDFs will be saved (default: "split_pdfs")
- `-d, --depth`: Maximum depth level for splitting (default: None, uses all levels)

### Examples

1. Split PDF using all bookmark levels (default behavior):
```bash
python split_pdf_by_bookmarks.py "document.pdf"
```

2. Split PDF at level 2 (chapters and sections, but not subsections):
```bash
python split_pdf_by_bookmarks.py "document.pdf" -d 2
```

3. Split PDF and save to custom directory:
```bash
python split_pdf_by_bookmarks.py "document.pdf" -o "output_folder"
```

4. Combine depth limit and custom output directory:
```bash
python split_pdf_by_bookmarks.py "document.pdf" -d 2 -o "chapters_only"
```

## Understanding Depth Levels

The depth level corresponds to the bookmark hierarchy in your PDF:

- Level 1: Main chapters (e.g., "1. Introduction")
- Level 2: Sections (e.g., "1.1 Background")
- Level 3: Subsections (e.g., "1.1.1 History")

Example of how different depth values affect splitting:

```
Original Structure:
1. Chapter One
   1.1 Section One
       1.1.1 Subsection A
       1.1.2 Subsection B
   1.2 Section Two
2. Chapter Two
   2.1 Section One

With -d 1:
- "Chapter One.pdf" (contains all content from 1.1 and 1.2)
- "Chapter Two.pdf" (contains all content from 2.1)

With -d 2:
- "Chapter One.pdf"
- "Section One.pdf" (contains 1.1.1 and 1.1.2)
- "Section Two.pdf"
- "Chapter Two.pdf"
- "Section One.pdf"

With no depth specified:
- "Chapter One.pdf"
- "Section One.pdf"
- "Subsection A.pdf"
- "Subsection B.pdf"
- "Section Two.pdf"
- "Chapter Two.pdf"
- "Section One.pdf"
```

## Output

- The script creates a directory (default: "split_pdfs" or as specified by -o)
- Each bookmark becomes a separate PDF file
- Filenames are created from bookmark titles, with special characters replaced by underscores
- The script preserves the page order and content of the original PDF

## Error Handling

- If the input file doesn't exist, the script will show an error message
- If no bookmarks are found in the PDF, the script will notify you
- Invalid depth values will be handled gracefully

## Limitations

- The script requires that the PDF has a proper bookmark structure
- Very long bookmark titles will be truncated to 150 characters in filenames
- Some special characters in bookmark titles will be replaced with underscores in filenames

## Tips

1. Always backup your original PDF before splitting
2. Use the --help option to see all available parameters:
```bash
python split_pdf_by_bookmarks.py --help
```
3. Start with no depth limit to see the full structure, then use -d parameter to get desired granularity
4. Check the output directory after splitting to ensure all files were created as expected

## Troubleshooting

If you encounter issues:

1. Ensure your PDF has bookmarks (Table of Contents)
2. Check that you have write permissions in the output directory
3. Verify that the input PDF path is correct
4. Make sure you have enough disk space for the split files