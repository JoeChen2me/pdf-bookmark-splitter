import os
import argparse
from PyPDF2 import PdfReader, PdfWriter
from collections import defaultdict

def process_bookmark(bookmark, reader):
    """Process a single bookmark and return its information"""
    if isinstance(bookmark, dict):
        if '/Page' in bookmark:
            title = bookmark.get('/Title', '')
            page_ref = bookmark.get('/Page', None)
            if hasattr(page_ref, 'get_object'):
                page_num = reader.get_page_number(page_ref.get_object())
            else:
                page_num = reader.get_page_number(page_ref)
            return [(title, page_num, title.count('.'))]
        return []
    elif isinstance(bookmark, list):
        results = []
        for b in bookmark:
            results.extend(process_bookmark(b, reader))
        return results
    return []

def extract_bookmarks_with_pages(reader):
    """Extract all bookmarks with their page numbers and levels"""
    def process_outline(outline):
        results = []
        if isinstance(outline, list):
            for item in outline:
                results.extend(process_outline(item))
        elif isinstance(outline, dict):
            title = outline.get('/Title', '')
            if '/Page' in outline:  # This is a page reference
                page_ref = outline['/Page']
                if hasattr(page_ref, 'get_object'):
                    page_num = reader.get_page_number(page_ref.get_object())
                else:
                    page_num = reader.get_page_number(page_ref)
                level = len(title.split('.')[0].strip().split())
                results.append((title, page_num, level))
            
            # Process any children
            if '/First' in outline:
                child = outline['/First']
                while child:
                    results.extend(process_outline(child))
                    child = child.get('/Next', None)
        
        return results

    try:
        outline = reader.outline
        if isinstance(outline, (list, dict)):
            return process_outline(outline)
        else:
            print("Warning: Outline structure not recognized")
            return []
    except Exception as e:
        print(f"Warning: Error processing outline: {str(e)}")
        return []

def organize_by_level(bookmarks, max_depth=None):
    """Organize bookmarks by their hierarchy level and merge deeper levels if max_depth is specified"""
    if not bookmarks:
        return []

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
            sections[current_parent].append((page_num, page_num))
        elif current_parent:
            if sections[current_parent]:
                sections[current_parent][-1] = (sections[current_parent][-1][0], page_num)

    # Convert to format needed for splitting
    result = []
    for title in sorted(sections.keys(), key=lambda x: sections[x][0][0]):
        result.append((title, sections[title][0][0]))
    
    return result

def split_pdf_by_bookmarks(input_pdf_path, output_dir="split_pdfs", max_depth=None):
    """Split a PDF file according to its bookmarks"""
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    # Statistics counters
    non_empty_count = 0
    empty_count = 0
    empty_chapters = []
    
    # Read the PDF
    print(f"Opening PDF: {input_pdf_path}")
    try:
        reader = PdfReader(input_pdf_path)
        print(f"PDF loaded successfully: {len(reader.pages)} pages")
    except Exception as e:
        print(f"Error opening PDF: {str(e)}")
        return
    
    # Get bookmarks with their page numbers and levels
    print("Extracting bookmarks...")
    bookmarks = extract_bookmarks_with_pages(reader)
    
    if not bookmarks:
        print("No bookmarks found in the PDF!")
        return
    
    print(f"Found {len(bookmarks)} bookmarks")
    
    # Organize bookmarks according to max_depth
    organized_bookmarks = organize_by_level(bookmarks, max_depth)
    print(f"Processing {len(organized_bookmarks)} sections")
    
    # Create splits based on organized bookmarks
    for i, (title, start_page) in enumerate(organized_bookmarks):
        # Get end page (either next bookmark's page or last page)
        end_page = organized_bookmarks[i + 1][1] if i < len(organized_bookmarks) - 1 else len(reader.pages)
        
        # Calculate number of pages
        num_pages = end_page - start_page
        
        # Skip empty documents (0 pages)
        if num_pages <= 0:
            empty_count += 1
            empty_chapters.append(title)
            continue
        
        # Create a new PDF
        writer = PdfWriter()
        
        # Add pages
        for page_num in range(start_page, end_page):
            if page_num < len(reader.pages):
                writer.add_page(reader.pages[page_num])
        
        # Clean filename
        safe_title = "".join(c if c.isalnum() or c in (' ', '-', '_') else '_' for c in title)
        safe_title = safe_title[:150]  # Limit filename length
        output_path = os.path.join(output_dir, f"{safe_title}.pdf")
        
        # Save the split PDF
        print(f"Creating: {safe_title}.pdf ({num_pages} pages)")
        try:
            with open(output_path, 'wb') as output_file:
                writer.write(output_file)
            non_empty_count += 1
        except Exception as e:
            print(f"Error saving '{safe_title}.pdf': {str(e)}")

    # Print statistics
    print("\nProcessing Summary:")
    print(f"Total sections processed: {len(organized_bookmarks)}")
    print(f"Non-empty documents created: {non_empty_count}")
    print(f"Empty sections skipped: {empty_count}")
    if empty_count > 0:
        print("\nSkipped sections (0 pages):")
        for chapter in empty_chapters:
            print(f"- {chapter}")

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
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()