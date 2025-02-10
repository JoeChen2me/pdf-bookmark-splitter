import os
import argparse
from PyPDF2 import PdfReader, PdfWriter
from collections import defaultdict

def get_bookmark_level(title):
    """Calculate the level of a bookmark based on its numbering"""
    parts = title.split()[0].split('.')
    return len([p for p in parts if p.replace(' ', '').isalnum()])

def extract_bookmarks_with_pages(reader, bookmark_list=None, parent_title="", current_depth=0):
    if bookmark_list is None:
        bookmark_list = reader.outline
    
    results = []
    
    for item in bookmark_list:
        if isinstance(item, list):
            results.extend(extract_bookmarks_with_pages(reader, item, parent_title, current_depth))
        else:
            if "/Page" in item:  # Check if it's actually a page reference
                title = item.title
                page_number = reader.get_destination_page_number(item)
                level = get_bookmark_level(title)
                results.append((title, page_number, level))
            
            if item.children:
                results.extend(extract_bookmarks_with_pages(reader, item.children, item.title, current_depth + 1))
    
    return results

def organize_by_level(bookmarks, max_depth=None):
    """
    Organize bookmarks by their hierarchy level and merge deeper levels if max_depth is specified
    
    Args:
        bookmarks: List of (title, page_number, level) tuples
        max_depth: Maximum depth level to preserve (None means keep all levels)
    """
    if not max_depth:
        return [(title, page_num) for title, page_num, _ in bookmarks]

    # Sort bookmarks by page number to ensure correct order
    bookmarks = sorted(bookmarks, key=lambda x: x[1])
    
    # Group bookmarks by their parent section
    sections = defaultdict(list)
    current_parent = None
    
    for title, page_num, level in bookmarks:
        if level <= max_depth:
            current_parent = title
            sections[current_parent].append((page_num, page_num))  # start and current page
        elif current_parent:
            # Extend the page range of the parent section
            if sections[current_parent]:
                sections[current_parent][-1] = (sections[current_parent][-1][0], page_num)

    # Convert to format needed for splitting
    result = []
    for title in sorted(sections.keys(), key=lambda x: sections[x][0][0]):
        result.append((title, sections[title][0][0]))
    
    return result

def split_pdf_by_bookmarks(input_pdf_path, output_dir="split_pdfs", max_depth=None):
    """
    Split a PDF file according to its bookmarks
    
    Args:
        input_pdf_path (str): Path to the input PDF file
        output_dir (str): Directory where split PDFs will be saved (default: "split_pdfs")
        max_depth (int): Maximum depth level for splitting (default: None, means use all levels)
    """
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    # Read the PDF
    print(f"Opening PDF: {input_pdf_path}")
    reader = PdfReader(input_pdf_path)
    
    # Get bookmarks with their page numbers and levels
    print("Extracting bookmarks...")
    bookmarks = extract_bookmarks_with_pages(reader)
    
    if not bookmarks:
        print("No bookmarks found in the PDF!")
        return
    
    # Organize bookmarks according to max_depth
    organized_bookmarks = organize_by_level(bookmarks, max_depth)
    print(f"Processing {len(organized_bookmarks)} sections")
    
    # Create splits based on organized bookmarks
    for i, (title, start_page) in enumerate(organized_bookmarks):
        # Get end page (either next bookmark's page or last page)
        end_page = organized_bookmarks[i + 1][1] if i < len(organized_bookmarks) - 1 else len(reader.pages)
        
        # Create a new PDF
        writer = PdfWriter()
        
        # Add pages
        for page_num in range(start_page, end_page):
            writer.add_page(reader.pages[page_num])
        
        # Clean filename
        safe_title = "".join(c if c.isalnum() or c in (' ', '-', '_') else '_' for c in title)
        safe_title = safe_title[:150]  # Limit filename length
        output_path = os.path.join(output_dir, f"{safe_title}.pdf")
        
        # Save the split PDF
        print(f"Creating: {safe_title}.pdf ({end_page - start_page} pages)")
        with open(output_path, 'wb') as output_file:
            writer.write(output_file)

def main():
    # Set up command line argument parser
    parser = argparse.ArgumentParser(description='Split PDF file according to its bookmarks')
    parser.add_argument('input_pdf', help='Path to the input PDF file')
    parser.add_argument('-o', '--output-dir', default='split_pdfs',
                        help='Directory where split PDFs will be saved (default: split_pdfs)')
    parser.add_argument('-d', '--depth', type=int, default=None,
                        help='Maximum depth level for splitting (e.g., 2 for splitting at second level headers). '
                             'Default: None (use all levels)')
    
    # Parse arguments
    args = parser.parse_args()
    
    # Check if input file exists
    if not os.path.exists(args.input_pdf):
        print(f"Error: Could not find input file '{args.input_pdf}'")
        return
    
    # Split the PDF
    try:
        split_pdf_by_bookmarks(args.input_pdf, args.output_dir, args.depth)
        print(f"\nPDF splitting complete! Check the '{args.output_dir}' directory for the output files.")
    except Exception as e:
        print(f"Error processing PDF: {str(e)}")

if __name__ == "__main__":
    main()