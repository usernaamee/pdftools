#!/usr/bin/env python3

import argparse
import os
import shutil
import logging
from tempfile import NamedTemporaryFile

try:
    from pypdf import PdfReader, PdfWriter, PdfMerger
    from pypdf.errors import PdfReadError
except ImportError:
    print("pypdf library not found. Please install it: pip install pypdf")
    exit(1)

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def parse_page_range(range_str: str, total_pages: int) -> list[int]:
    """
    Parses a page range string (e.g., "1-5,7,9-end") into a list of 0-indexed page numbers.
    Args:
        range_str: The page range string.
        total_pages: The total number of pages in the PDF (1-indexed context).
    Returns:
        A sorted list of unique 0-indexed page numbers.
    Raises:
        ValueError: If the page range string is invalid or out of bounds.
    """
    if not range_str:
        return []
    indices = set()
    # Normalize: allow "all" to mean all pages
    if range_str.strip().lower() == "all":
        return list(range(total_pages))

    parts = range_str.split(',')
    for part in parts:
        part = part.strip().lower()
        if not part:
            continue
        if '-' in part:
            start_str, end_str = part.split('-', 1)
            try:
                # Handle "end" keyword for start and end of range
                start = total_pages if start_str == 'end' else int(start_str)
                end = total_pages if end_str == 'end' else int(end_str)
            except ValueError:
                raise ValueError(f"Invalid page number in range: '{part}'")

            if not (1 <= start <= total_pages and 1 <= end <= total_pages):
                # Check even if total_pages is 0, though parse_page_range is usually called after checking total_pages > 0
                if total_pages == 0 and (start !=0 or end != 0): # Special case for empty PDF, only "0" or empty range is valid
                     raise ValueError(f"Page numbers in '{part}' out of bounds for an empty PDF.")
                elif total_pages > 0:
                     raise ValueError(f"Page numbers in '{part}' out of bounds (1-{total_pages}).")


            if start > end: # Allow reverse ranges like 5-1 to mean 1,2,3,4,5
                start, end = end, start 
            
            for i in range(start, end + 1):
                indices.add(i - 1) # Convert to 0-indexed
        else:
            try:
                page_num = total_pages if part == 'end' else int(part)
            except ValueError:
                raise ValueError(f"Invalid page number: '{part}'")
            
            if not (1 <= page_num <= total_pages):
                if total_pages == 0 and page_num != 0:
                    raise ValueError(f"Page number '{part}' out of bounds for an empty PDF.")
                elif total_pages > 0:
                    raise ValueError(f"Page number '{part}' out of bounds (1-{total_pages}).")
            indices.add(page_num - 1) # Convert to 0-indexed
    return sorted(list(indices))

def extract_pdf_pages(input_path: str, output_path: str, page_range_str: str, overwrite_global: bool = False):
    """Extracts specified pages from input_path to output_path."""
    try:
        if os.path.abspath(input_path) == os.path.abspath(output_path):
            logger.error("Input and output paths cannot be the same for extraction. Please choose a different output path.")
            return

        if os.path.exists(output_path) and not overwrite_global:
            logger.error(f"Output file '{output_path}' already exists. Use --overwrite to replace it.")
            return

        reader = PdfReader(input_path)
        total_pages = len(reader.pages)
        
        if total_pages == 0 and page_range_str.strip().lower() != "all" and page_range_str.strip() != "":
             logger.warning(f"Input PDF '{input_path}' is empty. Cannot extract specific pages.")
             # Create empty PDF if output is requested for empty input with empty/all range
             if page_range_str.strip().lower() == "all" or page_range_str.strip() == "":
                 PdfWriter().write(output_path)
                 logger.info(f"Input PDF '{input_path}' is empty. Created an empty output PDF at '{output_path}'.")
             return
        elif total_pages == 0: # Empty input, "all" or empty range
            PdfWriter().write(output_path)
            logger.info(f"Input PDF '{input_path}' is empty. Created an empty output PDF at '{output_path}'.")
            return


        page_indices = parse_page_range(page_range_str, total_pages)
        if not page_indices:
            logger.warning(f"No pages selected for extraction from '{input_path}' with range '{page_range_str}'. Output PDF '{output_path}' will be empty.")
            PdfWriter().write(output_path) # Create an empty PDF
            return

        writer = PdfWriter()
        for index in page_indices:
            writer.add_page(reader.pages[index])
        
        with open(output_path, "wb") as f_out:
            writer.write(f_out)
        logger.info(f"Successfully extracted pages '{page_range_str}' from '{input_path}' to '{output_path}'.")

    except FileNotFoundError:
        logger.error(f"Error: Input PDF file '{input_path}' not found.")
    except PdfReadError:
        logger.error(f"Error: Could not read PDF '{input_path}'. It may be corrupted or password-protected.")
    except ValueError as e:
        logger.error(f"Error in page range or PDF structure: {e}")
    except Exception as e:
        logger.error(f"An unexpected error occurred during extraction: {e}")

def cut_pdf_pages(input_path: str, output_path: str, page_range_to_cut_str: str, overwrite: bool = False):
    """Removes specified pages from input_path and saves the rest to output_path."""
    temp_file_path = None
    try:
        reader = PdfReader(input_path)
        total_pages = len(reader.pages)

        is_inplace_modification = os.path.abspath(input_path) == os.path.abspath(output_path)

        if is_inplace_modification and not overwrite:
            logger.error(f"Error: Input and output paths are the same ('{input_path}'). Use --overwrite to modify in place.")
            return
        if not is_inplace_modification and os.path.exists(output_path) and not overwrite:
            logger.error(f"Error: Output file '{output_path}' already exists. Use --overwrite to replace it.")
            return
            
        if total_pages == 0:
            logger.warning(f"Input PDF '{input_path}' is empty. Nothing to cut.")
            if not is_inplace_modification: # If output is different, copy empty file
                shutil.copyfile(input_path, output_path)
                logger.info(f"Input PDF empty. Copied empty PDF to '{output_path}'.")
            return

        indices_to_cut = set(parse_page_range(page_range_to_cut_str, total_pages))
        
        if not indices_to_cut:
            logger.info(f"No pages specified to cut from '{input_path}' (range: '{page_range_to_cut_str}').")
            if not is_inplace_modification:
                 shutil.copyfile(input_path, output_path)
                 logger.info(f"PDF copied to '{output_path}' without changes.")
            # If inplace and no pages to cut, it's a no-op.
            return

        writer = PdfWriter()
        pages_kept_count = 0
        for i in range(total_pages):
            if i not in indices_to_cut:
                writer.add_page(reader.pages[i])
                pages_kept_count += 1
        
        if pages_kept_count == 0:
            logger.warning(f"All pages from '{input_path}' were specified to be cut. Output '{output_path}' will be empty.")
        elif pages_kept_count == total_pages:
             logger.info(f"Specified pages to cut ('{page_range_to_cut_str}') resulted in no pages being removed. PDF remains unchanged.")
             if not is_inplace_modification:
                 shutil.copyfile(input_path, output_path)
                 logger.info(f"PDF copied to '{output_path}' without changes.")
             return # No changes needed

        # Proceed to write
        if is_inplace_modification: # Already checked for overwrite flag
            with NamedTemporaryFile(delete=False, suffix=".pdf", dir=os.path.dirname(input_path) or '.') as tmpfile:
                temp_file_path = tmpfile.name
                writer.write(tmpfile)
            shutil.move(temp_file_path, input_path)
            logger.info(f"Successfully cut pages '{page_range_to_cut_str}' from '{input_path}' (overwritten).")
        else:
            with open(output_path, "wb") as f_out:
                writer.write(f_out)
            logger.info(f"Successfully cut pages '{page_range_to_cut_str}' from '{input_path}' and saved to '{output_path}'.")

    except FileNotFoundError:
        logger.error(f"Error: Input PDF file '{input_path}' not found.")
    except PdfReadError:
        logger.error(f"Error: Could not read PDF '{input_path}'. It may be corrupted.")
    except ValueError as e:
        logger.error(f"Error in page range: {e}")
    except Exception as e:
        logger.error(f"An unexpected error occurred during cut: {e}")
        if temp_file_path and os.path.exists(temp_file_path):
            os.remove(temp_file_path)

def paste_pdf_pages(target_pdf_path: str, source_pdf_path: str, output_pdf_path: str, 
                    insert_before_page: int, source_page_range_str: str = None, overwrite: bool = False):
    """Pastes pages from source_pdf into target_pdf, saving to output_pdf."""
    temp_output_file_path = None
    temp_source_subset_path = None

    try:
        is_output_target = os.path.abspath(output_pdf_path) == os.path.abspath(target_pdf_path)
        is_output_source = os.path.abspath(output_pdf_path) == os.path.abspath(source_pdf_path)

        if (is_output_target or is_output_source) and not overwrite:
            logger.error(f"Error: Output path '{output_pdf_path}' is the same as an input PDF. Use --overwrite to modify in place.")
            return
        if not (is_output_target or is_output_source) and os.path.exists(output_pdf_path) and not overwrite:
            logger.error(f"Error: Output file '{output_pdf_path}' already exists. Use --overwrite to replace it.")
            return

        target_reader = PdfReader(target_pdf_path)
        source_reader = PdfReader(source_pdf_path)
        
        num_target_pages = len(target_reader.pages)
        num_source_pages = len(source_reader.pages)

        # insert_before_page is 1-indexed, can be num_target_pages + 1 for appending
        if not (1 <= insert_before_page <= num_target_pages + 1):
            logger.error(f"Error: Insert position '{insert_before_page}' is out of bounds for target PDF with {num_target_pages} pages (should be 1 to {num_target_pages + 1}).")
            return

        # Prepare source pages to paste
        pages_from_source_obj = source_reader # Default to all pages from source reader
        if source_page_range_str:
            if num_source_pages == 0:
                logger.warning(f"Source PDF '{source_pdf_path}' is empty. No pages to paste from specified range '{source_page_range_str}'.")
                # Effectively, this means only the target PDF will be written to output.
                # Let merger handle target_pdf_path directly.
                pages_from_source_obj = None # Indicate no source pages
            else:
                source_indices = parse_page_range(source_page_range_str, num_source_pages)
                if not source_indices:
                    logger.warning(f"Source page range '{source_page_range_str}' is empty or invalid for source PDF '{source_pdf_path}'. No pages will be pasted from source.")
                    pages_from_source_obj = None # Indicate no source pages
                else:
                    source_subset_writer = PdfWriter()
                    for index in source_indices:
                        source_subset_writer.add_page(source_reader.pages[index])
                    
                    # Create a temporary PDF for the subset of source pages
                    with NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_s:
                        temp_source_subset_path = tmp_s.name
                        source_subset_writer.write(tmp_s)
                    pages_from_source_obj = temp_source_subset_path # Path to the temporary PDF
        elif num_source_pages == 0: # No range specified, but source is empty
             logger.warning(f"Source PDF '{source_pdf_path}' is empty. No pages to paste.")
             pages_from_source_obj = None


        # Perform the merge/paste operation
        merger = PdfMerger()
        merger.append(target_pdf_path) # Add all pages from target
        
        if pages_from_source_obj:
            # Check if the object (path or reader) actually has pages
            source_to_merge_reader = PdfReader(pages_from_source_obj) if isinstance(pages_from_source_obj, str) else pages_from_source_obj
            if len(source_to_merge_reader.pages) > 0:
                 # PdfMerger.merge position is 0-indexed. insert_before_page is 1-indexed.
                merge_position = insert_before_page - 1
                merger.merge(position=merge_position, fileobj=source_to_merge_reader)
            else:
                logger.warning(f"No effective source pages from '{source_pdf_path}' (range: '{source_page_range_str}') to paste.")
        else: # No source pages to paste (either empty source, or empty range)
            logger.info("No source pages to paste. Output will effectively be the target PDF.")


        # Write the result
        final_write_path = output_pdf_path
        if is_output_target or is_output_source: # Overwriting an input
            with NamedTemporaryFile(delete=False, suffix=".pdf", dir=os.path.dirname(output_pdf_path) or '.') as tmp_o:
                temp_output_file_path = tmp_o.name
                merger.write(tmp_o)
            shutil.move(temp_output_file_path, output_pdf_path)
            temp_output_file_path = None 
            logger.info(f"Successfully pasted pages, result saved to '{output_pdf_path}' (overwritten).")
        else:
            with open(output_pdf_path, "wb") as f_out:
                merger.write(f_out)
            logger.info(f"Successfully pasted pages, result saved to '{output_pdf_path}'.")
        
        merger.close()

    except FileNotFoundError as e:
        logger.error(f"Error: PDF file not found: {e.filename}")
    except PdfReadError as e:
        logger.error(f"Error: Could not read PDF. It may be corrupted or password-protected. Details: {e}")
    except ValueError as e:
        logger.error(f"Error in page range or number: {e}")
    except Exception as e:
        logger.error(f"An unexpected error occurred during paste: {e}")
    finally:
        if temp_source_subset_path and os.path.exists(temp_source_subset_path):
            os.remove(temp_source_subset_path)
        if temp_output_file_path and os.path.exists(temp_output_file_path):
            os.remove(temp_output_file_path)

def split_pdf_pages(input_path: str, output_dir: str, mode: str = "each_page", 
                    ranges_csv: str = None, overwrite_global: bool = False):
    """Splits input_path into multiple PDFs in output_dir."""
    try:
        reader = PdfReader(input_path)
        total_pages = len(reader.pages)
        if total_pages == 0:
            logger.warning(f"Input PDF '{input_path}' is empty. Nothing to split.")
            return

        os.makedirs(output_dir, exist_ok=True)
        base_name = os.path.splitext(os.path.basename(input_path))[0]

        if mode == "each_page":
            for i, page in enumerate(reader.pages):
                output_filename = os.path.join(output_dir, f"{base_name}_page_{i + 1}.pdf")
                if os.path.exists(output_filename) and not overwrite_global:
                    logger.error(f"Output file '{output_filename}' already exists. Use --overwrite or clear directory. Skipping.")
                    continue
                
                writer = PdfWriter()
                writer.add_page(page)
                with open(output_filename, "wb") as f_out:
                    writer.write(f_out)
            logger.info(f"Successfully split '{input_path}' into individual pages in directory '{output_dir}'.")
        
        elif mode == "ranges":
            if not ranges_csv:
                logger.error("Error: For 'ranges' split mode, --ranges_spec must be provided.")
                return
            
            # Example: "1-3;4-5;6-end" -> ranges are "1-3", "4-5", "6-end"
            range_specs = ranges_csv.split(';') 
            for i, range_str_part in enumerate(range_specs):
                range_str_part = range_str_part.strip()
                if not range_str_part: continue

                page_indices = parse_page_range(range_str_part, total_pages)
                if not page_indices:
                    logger.warning(f"Range '{range_str_part}' for split resulted in no pages. Skipping.")
                    continue
                
                # Sanitize range_str_part for filename
                safe_range_name = range_str_part.replace('-', '_to_').replace(',', '_').replace(' ','')
                output_filename = os.path.join(output_dir, f"{base_name}_range_{i+1}_{safe_range_name}.pdf")

                if os.path.exists(output_filename) and not overwrite_global:
                    logger.error(f"Output file '{output_filename}' already exists. Use --overwrite or clear directory. Skipping.")
                    continue

                writer = PdfWriter()
                for index in page_indices:
                    writer.add_page(reader.pages[index])
                with open(output_filename, "wb") as f_out:
                    writer.write(f_out)
            logger.info(f"Successfully split '{input_path}' by ranges '{ranges_csv}' into directory '{output_dir}'.")
        else:
            logger.error(f"Unknown split mode: {mode}. Choose 'each_page' or 'ranges'.")

    except FileNotFoundError:
        logger.error(f"Error: Input PDF file '{input_path}' not found.")
    except PdfReadError:
        logger.error(f"Error: Could not read PDF '{input_path}'. It may be corrupted.")
    except ValueError as e:
        logger.error(f"Error in page range: {e}")
    except Exception as e:
        logger.error(f"An unexpected error occurred during split: {e}")

def merge_pdf_files(input_paths: list[str], output_path: str, overwrite: bool = False):
    """Merges multiple input_paths into output_path."""
    merger = PdfMerger()
    try:
        if not input_paths:
            logger.error("Error: No input PDF files provided for merging.")
            return
        
        abs_output_path = os.path.abspath(output_path)
        is_output_an_input = any(abs_output_path == os.path.abspath(p) for p in input_paths)

        if is_output_an_input and not overwrite:
            logger.error(f"Error: Output path '{output_path}' is the same as an input PDF. Use --overwrite to modify in place or choose a different output path.")
            return
        if not is_output_an_input and os.path.exists(output_path) and not overwrite:
            logger.error(f"Error: Output file '{output_path}' already exists. Use --overwrite to replace it.")
            return

        valid_inputs_count = 0
        for pdf_path in input_paths:
            try:
                # Check if file is empty or unreadable before appending
                if not os.path.exists(pdf_path):
                     logger.error(f"Error: Input PDF file '{pdf_path}' not found. Skipping.")
                     continue
                if os.path.getsize(pdf_path) == 0:
                    logger.warning(f"Input PDF '{pdf_path}' is empty (0 bytes). Skipping.")
                    continue

                current_reader = PdfReader(pdf_path) # Check readability
                if len(current_reader.pages) == 0:
                    logger.warning(f"Input PDF '{pdf_path}' has no pages. It will be skipped in the merge.")
                    continue
                merger.append(pdf_path)
                valid_inputs_count +=1
            except FileNotFoundError: # Should be caught by os.path.exists, but defensive
                logger.error(f"Error: Input PDF file '{pdf_path}' not found. Skipping.")
            except PdfReadError:
                logger.error(f"Error: Could not read PDF '{pdf_path}'. It may be corrupted. Skipping.")
            except Exception as e_inner: # Catch other potential errors with individual files
                logger.error(f"Error processing file '{pdf_path}': {e_inner}. Skipping.")
        
        if valid_inputs_count == 0:
            logger.error("No valid PDF files to merge. Output will not be created/modified.")
            merger.close()
            return

        # Write merged PDF
        # If output_path is an input path, it's an overwrite scenario.
        # PdfMerger.write handles overwriting the file directly.
        with open(output_path, "wb") as f_out:
            merger.write(f_out)
        logger.info(f"Successfully merged {valid_inputs_count} PDF(s) into '{output_path}'.")

    except Exception as e:
        logger.error(f"An unexpected error occurred during merge: {e}")
    finally:
        merger.close()


def main():
    parser = argparse.ArgumentParser(description="Python PDF Manipulation Tool (pdfmanip.py)")
    parser.add_argument('--overwrite', action='store_true', 
                        help="Allow overwriting output files if they already exist or if an output path is the same as an input path.")
    
    subparsers = parser.add_subparsers(dest="command", required=True, help="Available commands")

    # Extract
    extract_parser = subparsers.add_parser("extract", help="Extract a range of pages from a PDF.")
    extract_parser.add_argument("input_pdf", help="Path to the input PDF file.")
    extract_parser.add_argument("output_pdf", help="Path to save the extracted PDF.")
    extract_parser.add_argument("-r", "--range", required=True, help="Page range to extract (e.g., '1-5,7,9-end', 'all').")

    # Cut
    cut_parser = subparsers.add_parser("cut", help="Cut (remove) a range of pages from a PDF.")
    cut_parser.add_argument("input_pdf", help="Path to the input PDF file.")
    cut_parser.add_argument("output_pdf", help="Path to save the PDF with pages cut.")
    cut_parser.add_argument("-r", "--range", required=True, help="Page range to cut (e.g., '1-3,5', 'all').")

    # Paste
    paste_parser = subparsers.add_parser("paste", help="Paste pages from one PDF into another.")
    paste_parser.add_argument("target_pdf", help="The PDF to paste into.")
    paste_parser.add_argument("source_pdf", help="The PDF to take pages from.")
    paste_parser.add_argument("output_pdf", help="Path to save the resulting PDF.")
    paste_parser.add_argument("-at", "--insert_before_page", required=True, type=int, help="1-indexed page number in the target PDF before which pages will be inserted (e.g., 1 for beginning, <num_target_pages>+1 for end).")
    paste_parser.add_argument("-sr", "--source_range", help="Optional: Page range from the source PDF to paste (e.g., '1-2,4', 'all'). Defaults to all pages from source.", default=None)

    # Split
    split_parser = subparsers.add_parser("split", help="Split a PDF into multiple files.")
    split_parser.add_argument("input_pdf", help="Path to the input PDF file.")
    split_parser.add_argument("output_dir", help="Directory to save the split PDF files.")
    split_parser.add_argument("--mode", choices=["each_page", "ranges"], default="each_page", help="Split mode: 'each_page' (one file per page) or 'ranges'.")
    split_parser.add_argument("--ranges_spec", help="For 'ranges' mode, a semicolon-separated list of page ranges (e.g., '1-3;4-5;6-end'). Each range forms a new PDF.")

    # Merge
    merge_parser = subparsers.add_parser("merge", help="Merge multiple PDF files into one.")
    merge_parser.add_argument("output_pdf", help="Path to save the merged PDF.")
    merge_parser.add_argument("input_pdfs", nargs='+', help="Paths to the input PDF files to merge (at least one required).")

    args = parser.parse_args()
    overwrite_flag = args.overwrite

    if args.command == "extract":
        extract_pdf_pages(args.input_pdf, args.output_pdf, args.range, overwrite_global=overwrite_flag)
    elif args.command == "cut":
        cut_pdf_pages(args.input_pdf, args.output_pdf, args.range, overwrite=overwrite_flag)
    elif args.command == "paste":
        paste_pdf_pages(args.target_pdf, args.source_pdf, args.output_pdf, 
                        args.insert_before_page, args.source_range, overwrite=overwrite_flag)
    elif args.command == "split":
        split_pdf_pages(args.input_pdf, args.output_dir, args.mode, args.ranges_spec, overwrite_global=overwrite_flag)
    elif args.command == "merge":
        merge_pdf_files(args.input_pdfs, args.output_pdf, overwrite=overwrite_flag)

if __name__ == "__main__":
    main()
