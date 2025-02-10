import os
import argparse
import re
from PyPDF2 import PdfReader, PdfWriter
from collections import defaultdict

def detect_bookmark_pattern(title):
    """
    Detect the pattern of bookmark title and return its level
    Returns: (level, pattern_type)
    pattern_type: 'numeric' or 'text' or 'mixed'
    """
    # 检查数字格式 (1.1, 1.2, etc.)
    numeric_pattern = r'^(\d+\.)*\d+'
    if re.match(numeric_pattern, title.strip()):
        level = len(title.strip().split('.'))
        return level, 'numeric'
    
    # 检查中文章节格式
    chapter_patterns = {
        r'^第[一二三四五六七八九十百千]+章': 1,  # 第一章
        r'^第[一二三四五六七八九十百千]+节': 2,  # 第一节
        r'^第[一二三四五六七八九十百千]+小节': 3,  # 第一小节
        r'^[一二三四五六七八九十]、': 1,  # 一、二、三、
        r'^（[一二三四五六七八九十]）': 2,  # （一）（二）
        r'^\([1-9][0-9]*\)': 2,  # (1)(2)
        r'^[1-9][0-9]*\. ': 1,  # 1. 2.
        r'^[a-zA-Z]\. ': 2,  # a. b.
    }
    
    for pattern, level in chapter_patterns.items():
        if re.match(pattern, title.strip()):
            return level, 'text'
    
    # 检查是否包含数字和文字的混合格式
    mixed_pattern = r'^\d+\s*[、.\s]?\s*[第章节]'
    if re.match(mixed_pattern, title.strip()):
        return 1, 'mixed'
    
    # 检查其他常见格式
    special_patterns = {
        r'^前言$': 1,
        r'^引言$': 1,
        r'^简介$': 1,
        r'^附录[A-Za-z]?': 1,
        r'^总结$': 1,
        r'^参考文献$': 1,
    }
    
    for pattern, level in special_patterns.items():
        if re.match(pattern, title.strip()):
            return level, 'special'
    
    # 如果没有找到匹配的模式，尝试通过缩进或其他特征判断
    indent_level = len(title) - len(title.lstrip())
    if indent_level > 0:
        return (indent_level // 2) + 1, 'indent'
    
    # 默认为最底层
    return 1, 'unknown'

def analyze_bookmark_structure(bookmarks):
    """分析书签结构，确定主要使用的格式类型"""
    pattern_counts = defaultdict(int)
    for title, _, _ in bookmarks:
        _, pattern_type = detect_bookmark_pattern(title)
        pattern_counts[pattern_type] += 1
    
    # 返回最常用的格式类型
    if pattern_counts:
        main_pattern = max(pattern_counts.items(), key=lambda x: x[1])[0]
        return main_pattern
    return 'unknown'

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
                try:
                    if hasattr(page_ref, 'get_object'):
                        page_num = reader.get_page_number(page_ref.get_object())
                    else:
                        page_num = reader.get_page_number(page_ref)
                    
                    level, _ = detect_bookmark_pattern(title)
                    results.append((title, page_num, level))
                except Exception as e:
                    print(f"Warning: Error processing page reference for '{title}': {str(e)}")
            
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
            bookmarks = process_outline(outline)
            # 分析书签结构
            main_pattern = analyze_bookmark_structure(bookmarks)
            print(f"Detected main bookmark pattern: {main_pattern}")
            return bookmarks
        else:
            print("Warning: Outline structure not recognized")
            return []
    except Exception as e:
        print(f"Warning: Error processing outline: {str(e)}")
        return []

def organize_by_level(bookmarks, max_depth=None):
    """Organize bookmarks by their hierarchy level"""
    if not bookmarks:
        return []

    # 分析书签结构
    main_pattern = analyze_bookmark_structure(bookmarks)
    print(f"Using bookmark pattern: {main_pattern}")

    if not max_depth:
        return [(title, page_num) for title, page_num, _ in bookmarks]

    # 按页码排序确保顺序正确
    bookmarks = sorted(bookmarks, key=lambda x: x[1])
    
    sections = defaultdict(list)
    current_parent = None
    
    for title, page_num, level in bookmarks:
        if level <= max_depth:
            current_parent = title
            sections[current_parent].append((page_num, page_num))
        elif current_parent:
            if sections[current_parent]:
                sections[current_parent][-1] = (sections[current_parent][-1][0], page_num)

    result = []
    for title in sorted(sections.keys(), key=lambda x: sections[x][0][0]):
        result.append((title, sections[title][0][0]))
    
    return result

def split_pdf_by_bookmarks(input_pdf_path, output_dir="split_pdfs", max_depth=None):
    """Split a PDF file according to its bookmarks"""
    os.makedirs(output_dir, exist_ok=True)
    
    # 统计计数器
    non_empty_count = 0
    empty_count = 0
    empty_chapters = []
    
    print(f"Opening PDF: {input_pdf_path}")
    try:
        reader = PdfReader(input_pdf_path)
        print(f"PDF loaded successfully: {len(reader.pages)} pages")
    except Exception as e:
        print(f"Error opening PDF: {str(e)}")
        return
    
    print("Extracting bookmarks...")
    bookmarks = extract_bookmarks_with_pages(reader)
    
    if not bookmarks:
        print("No bookmarks found in the PDF!")
        return
    
    print(f"Found {len(bookmarks)} bookmarks")
    
    organized_bookmarks = organize_by_level(bookmarks, max_depth)
    print(f"Processing {len(organized_bookmarks)} sections")
    
    for i, (title, start_page) in enumerate(organized_bookmarks):
        end_page = organized_bookmarks[i + 1][1] if i < len(organized_bookmarks) - 1 else len(reader.pages)
        
        # 计算页数
        num_pages = end_page - start_page
        
        # 跳过空白文档
        if num_pages <= 0:
            empty_count += 1
            empty_chapters.append(title)
            continue
        
        writer = PdfWriter()
        
        for page_num in range(start_page, end_page):
            if page_num < len(reader.pages):
                writer.add_page(reader.pages[page_num])
        
        safe_title = "".join(c if c.isalnum() or c in (' ', '-', '_') else '_' for c in title)
        safe_title = safe_title[:150]
        output_path = os.path.join(output_dir, f"{safe_title}.pdf")
        
        print(f"Creating: {safe_title}.pdf ({num_pages} pages)")
        try:
            with open(output_path, 'wb') as output_file:
                writer.write(output_file)
            non_empty_count += 1
        except Exception as e:
            print(f"Error saving '{safe_title}.pdf': {str(e)}")

    # 打印统计信息
    print("\nProcessing Summary:")
    print(f"Total sections processed: {len(organized_bookmarks)}")
    print(f"Non-empty documents created: {non_empty_count}")
    print(f"Empty sections skipped: {empty_count}")
    if empty_count > 0:
        print("\nSkipped sections (0 pages):")
        for chapter in empty_chapters:
            print(f"- {chapter}")

def main():
    parser = argparse.ArgumentParser(description='Split PDF file according to its bookmarks')
    parser.add_argument('input_pdf', help='Path to the input PDF file')
    parser.add_argument('-o', '--output-dir', default='split_pdfs',
                        help='Directory where split PDFs will be saved (default: split_pdfs)')
    parser.add_argument('-d', '--depth', type=int, default=None,
                        help='Maximum depth level for splitting (e.g., 2 for splitting at second level headers). '
                             'Default: None (use all levels)')
    
    args = parser.parse_args()
    
    if not os.path.exists(args.input_pdf):
        print(f"Error: Could not find input file '{args.input_pdf}'")
        return
    
    try:
        split_pdf_by_bookmarks(args.input_pdf, args.output_dir, args.depth)
        print(f"\nPDF splitting complete! Check the '{args.output_dir}' directory for the output files.")
    except Exception as e:
        print(f"Error processing PDF: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()