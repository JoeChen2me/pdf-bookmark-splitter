import os
import argparse
from PyPDF2 import PdfReader, PdfWriter
from collections import defaultdict

def debug_print_outline(outline, level=0):
    """Debug function to print outline structure"""
    if isinstance(outline, list):
        print("  " * level + "List of items:")
        for item in outline:
            debug_print_outline(item, level + 1)
    elif isinstance(outline, dict):
        print("  " * level + f"Dict item: {outline.get('/Title', 'No Title')}")
        if '/First' in outline:
            debug_print_outline(outline['/First'], level + 1)
        if '/Next' in outline:
            debug_print_outline(outline['/Next'], level)
    else:
        print("  " * level + f"Unknown type: {type(outline)}")

def extract_bookmarks_with_pages(reader):
    """Extract all bookmarks with their page numbers and levels"""
    def process_outline(outline, level=0):
        results = []
        if outline is None:
            return results

        if isinstance(outline, list):
            for item in outline:
                results.extend(process_outline(item, level))
        elif isinstance(outline, dict):
            title = outline.get('/Title', '')
            print(f"Processing bookmark: {title}")  # Debug info
            
            try:
                if '/Page' in outline or '/D' in outline:
                    # Try different ways to get the page number
                    page_num = None
                    if '/Page' in outline:
                        page_ref = outline['/Page']
                        if hasattr(reader, 'get_page_number'):
                            try:
                                page_num = reader.get_page_number(page_ref)
                            except:
                                # If direct method fails, try getting the object first
                                if hasattr(page_ref, 'get_object'):
                                    page_num = reader.get_page_number(page_ref.get_object())
                    elif '/D' in outline:
                        # Some PDFs use /D instead of /Page
                        dest = outline['/D']
                        if isinstance(dest, list) and len(dest) > 0:
                            page_ref = dest[0]
                            if hasattr(reader, 'get_page_number'):
                                try:
                                    page_num = reader.get_page_number(page_ref)
                                except:
                                    if hasattr(page_ref, 'get_object'):
                                        page_num = reader.get_page_number(page_ref.get_object())

                    if page_num is not None:
                        # Determine level based on title format (e.g., "1.2.3")
                        dots = title.split('.')
                        level = len(dots) if len(dots) > 1 else 1
                        results.append((title, page_num, level))
                        print(f"Added bookmark: {title} (Page {page_num}, Level {level})")  # Debug info
            except Exception as e:
                print(f"Warning: Error processing bookmark '{title}': {str(e)}")
            
            # Process child bookmarks
            if '/First' in outline:
                results.extend(process_outline(outline['/First'], level + 1))
            if '/Next' in outline:
                results.extend(process_outline(outline['/Next'], level))
        
        return results

    print("Starting bookmark extraction...")  # Debug info
    try:
        outline = reader.outline
        print(f"Outline type: {type(outline)}")  # Debug info
        debug_print_outline(outline)  # Print outline structure
        
        if outline is None:
            print("No outline found in PDF")
            return []
        
        results = process_outline(outline)
        print(f"Extracted {len(results)} bookmarks")  # Debug info
        return results
    except Exception as e:
        print(f"Error in bookmark extraction: {str(e)}")
        return []

def organize_by_level(bookmarks, max_depth=None):
    """
    Organize bookmarks by their hierarchy level and merge deeper levels if max_depth is specified
    """
    if not bookmarks:
        return []

    print(f"Organizing bookmarks with max_depth: {max_depth}")  # Debug info
    
    if not max_depth:
        result = [(title, page_num) for title, page_num, _ in bookmarks]
        print(f"Using all levels: {len(result)} bookmarks")  # Debug info
        return result

    # Sort bookmarks by page number to ensure correct order
    bookmarks = sorted(bookmarks, key=lambda x: x[1])
    
    # Group bookmarks by their parent section
    sections = defaultdict(list)
    current_parent = None
    
    for title, page_num, level in bookmarks:
        print(f"Processing: {title} (Level {level})")  # Debug info
        if level <= max_depth:
            current_parent = title
            sections[current_parent].append((page_num, page_num))
            print(f"New section: {current_parent}")  # Debug info
        elif current_parent:
            if sections[current_parent]:
                sections[current_parent][-1] = (sections[current_parent][-1][0], page_num)
                print(f"Extended section: {current_parent}")  # Debug info

    # Convert to format needed for splitting
    result = []
    for title in sorted(sections.keys(), key=lambda x: sections[x][0][0]):
        result.append((title, sections[title][0][0]))
    
    print(f"Organized into {len(result)} sections")  # Debug info
    return result

def split_pdf_by_bookmarks(input_pdf_path, output_dir="split_pdfs", max_depth=None):
    """
    Split a PDF file according to its bookmarks
    """
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    # Read the PDF
    print(f"Opening PDF: {input_pdf_path}")
    try:
        reader = PdfReader(input_pdf_path)
        print(f"PDF loaded successfully: {len(reader.pages)} pages")  # Debug info
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
        print(f"Creating: {safe_title}.pdf ({end_page - start_page} pages)")
        try:
            with open(output_path, 'wb') as output_file:
                writer.write(output_file)
        except Exception as e:
            print(f"Error saving '{safe_title}.pdf': {str(e)}")

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
        traceback.print_exc()  # Print full stack trace for debugging

if __name__ == "__main__":
    main()