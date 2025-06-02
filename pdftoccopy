import argparse
import sys
from PyPDF2 import PdfReader, PdfWriter
from PyPDF2.errors import PdfReadError

def _copy_bookmarks_recursive(reader_source, writer, source_outline_items, parent_writer_bookmark=None):
    """
    Recursively processes source PDF bookmarks and adds them to the writer.

    Args:
        reader_source (PdfReader): The reader object for the source PDF.
        writer (PdfWriter): The writer object for the output PDF.
        source_outline_items (list): The list of bookmark items from the source PDF's outline.
        parent_writer_bookmark (OutlineItem | None): The parent bookmark in the writer for nesting.
    """
    i = 0
    while i < len(source_outline_items):
        item = source_outline_items[i]

        # If 'item' is a list, it represents children of the *previous* item.
        # This case should be handled by the recursive call for the parent.
        # If we encounter it here, it implies an unexpected top-level list item
        # or incorrect parsing of PyPDF2's outline structure initially.
        # PyPDF2's reader.outline typically gives a flat list where sub-lists are children
        # of the *preceding* Destination object.
        if isinstance(item, list):
            # This typically shouldn't be hit if called correctly on a list of Destinations
            # or if the top-level outline_items isn't a list of lists.
            # It's more of a safeguard or indicates a misunderstanding of PyPDF2 structure.
            # Assuming if we hit a list, it's a list of children that should have been passed
            # to a recursive call by its parent.
            # For robustness, we can try to process its contents under the current parent.
            # print(f"Warning: Encountered a sub-list directly at current level. Processing its items.", file=sys.stderr)
            # _copy_bookmarks_recursive(reader_source, writer, item, parent_writer_bookmark)
            # However, the main loop structure (i+=1 after processing children) is designed
            # to handle this, so a direct list item here is unusual.
            i += 1
            continue

        title = item.title
        page_num_in_source = None

        try:
            # Attempt to get the page number this bookmark points to in the source PDF.
            page_num_in_source = reader_source.get_destination_page_number(item)
        except Exception as e: # pylint: disable=broad-except
            # Some bookmarks might not resolve to a page (e.g., broken, web links not handled here)
            print(f"Warning: Could not resolve page for bookmark '{title}'. Error: {e}. Skipping.", file=sys.stderr)
            i += 1
            continue

        if page_num_in_source is not None:
            # Add the current bookmark to the writer
            current_writer_bookmark = writer.add_outline_item(
                title,
                page_num_in_source,
                parent=parent_writer_bookmark
            )

            # Check if the *next* element in source_outline_items is a list,
            # which represents the children of the current 'item'.
            if (i + 1) < len(source_outline_items) and isinstance(source_outline_items[i+1], list):
                _copy_bookmarks_recursive(reader_source, writer, source_outline_items[i+1], current_writer_bookmark)
                i += 1 # Increment to skip the children list we just processed
        else:
            print(f"Warning: Bookmark '{title}' in source PDF does not point to a valid page. Skipping.", file=sys.stderr)

        i += 1

def copy_toc_to_pdf(source_pdf_path, destination_pdf_path, output_pdf_path):
    """
    Copies the table of contents (bookmarks) from a source PDF to a destination PDF.

    Args:
        source_pdf_path (str): Path to the PDF file to copy bookmarks from.
        destination_pdf_path (str): Path to the PDF file to copy bookmarks to.
        output_pdf_path (str): Path to save the modified destination PDF.

    Returns:
        bool: True if successful, False otherwise.
    """
    try:
        # Open the source PDF and get its bookmarks
        reader_source = PdfReader(source_pdf_path)
        source_outlines = reader_source.outline

        if not source_outlines:
            print(f"Info: No table of contents (bookmarks) found in '{source_pdf_path}'. Output PDF will not have new bookmarks.", file=sys.stderr)
            # Proceed to copy pages even if no bookmarks, to create output_pdf_path from destination_pdf_path
        else:
            print(f"Successfully read {len(source_outlines)} top-level bookmark item(s)/group(s) from '{source_pdf_path}'.")


        # Open the destination PDF and initialize writer
        reader_dest = PdfReader(destination_pdf_path)
        writer = PdfWriter()

        # Add all pages from the destination PDF to the writer
        for page in reader_dest.pages:
            writer.add_page(page)
        print(f"Copied {len(reader_dest.pages)} pages from '{destination_pdf_path}'.")

        # If there were bookmarks in the source, process and add them
        if source_outlines:
            _copy_bookmarks_recursive(reader_source, writer, source_outlines)
            print("Successfully processed and added bookmarks to the new PDF.")

        # Write the output PDF
        with open(output_pdf_path, "wb") as f_out:
            writer.write(f_out)
        print(f"Successfully wrote modified PDF to '{output_pdf_path}'.")
        return True

    except FileNotFoundError as e:
        print(f"Error: PDF file not found: {e.filename}", file=sys.stderr)
    except PdfReadError as e:
        print(f"Error: Could not read PDF: {e}. Ensure it's a valid PDF and not encrypted.", file=sys.stderr)
    except Exception as e: # pylint: disable=broad-except
        print(f"An unexpected error occurred: {e}", file=sys.stderr)
        # For a CLI tool, printing traceback can be helpful for users to report issues
        import traceback
        traceback.print_exc()
    return False

def main():
    """Main function to parse arguments and initiate TOC copying."""
    parser = argparse.ArgumentParser(
        description="Copy Table of Contents (Bookmarks) from one PDF to another.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument(
        "source_pdf",
        help="Path to the source PDF file (from which to copy the ToC)."
    )
    parser.add_argument(
        "destination_pdf",
        help="Path to the destination PDF file (to which the ToC will be added)."
    )
    parser.add_argument(
        "-o", "--output_pdf",
        help="Path for the output PDF file with the copied ToC.\n"
             "If not provided, it will overwrite the destination_pdf.",
        default=None
    )

    args = parser.parse_args()

    # If output_pdf is not specified, it defaults to overwriting the destination_pdf
    output_file = args.output_pdf if args.output_pdf else args.destination_pdf

    print(f"Source PDF:      {args.source_pdf}")
    print(f"Destination PDF: {args.destination_pdf}")
    print(f"Output PDF:      {output_file}")

    if copy_toc_to_pdf(args.source_pdf, args.destination_pdf, output_file):
        print("Operation completed successfully.")
        sys.exit(0)
    else:
        print("Operation failed.")
        sys.exit(1)

if __name__ == "__main__":
    main()
