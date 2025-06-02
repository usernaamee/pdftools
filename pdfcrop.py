import PyPDF2
import argparse
import os
import sys

POINTS_PER_INCH = 72.0  # Standard PDF points per inch

def crop_pdf_pages_centered(input_pdf_path: str, output_pdf_path: str, target_width_inches: float, target_height_inches: float):
    """
    Crops all pages of a PDF to a specified size (in inches), centered.
    If a page is smaller than the target dimensions, it will be cropped to its
    original dimensions (effectively no visual change for that page's content area).

    Args:
        input_pdf_path: Path to the input PDF file.
        output_pdf_path: Path to save the cropped PDF file.
        target_width_inches: The target width for cropping in inches.
        target_height_inches: The target height for cropping in inches.

    Raises:
        FileNotFoundError: If the input PDF file is not found.
        PyPDF2.errors.PdfReadError: If the input PDF cannot be read (e.g., corrupted, encrypted).
        IOError: If the output PDF cannot be written.
        Exception: For other unexpected errors during processing.
    """
    target_width_points = target_width_inches * POINTS_PER_INCH
    target_height_points = target_height_inches * POINTS_PER_INCH

    try:
        reader = PyPDF2.PdfReader(input_pdf_path)
        writer = PyPDF2.PdfWriter()

        num_pages = len(reader.pages)
        print(f"Processing {num_pages} pages...")
        print(f"Target crop dimensions: {target_width_inches}\"W x {target_height_inches}\"H "
              f"({target_width_points:.2f} x {target_height_points:.2f} points).")

        for i, page in enumerate(reader.pages):
            page_num = i + 1
            try:
                original_media_box = page.mediabox
                original_width_points = float(original_media_box.width)
                original_height_points = float(original_media_box.height)

                # Determine the actual crop dimensions for this page
                actual_crop_width_points = min(target_width_points, original_width_points)
                actual_crop_height_points = min(target_height_points, original_height_points)

                if original_width_points < target_width_points or original_height_points < target_height_points:
                    print(f"  Page {page_num} (Original: {original_width_points/POINTS_PER_INCH:.2f}\" x "
                          f"{original_height_points/POINTS_PER_INCH:.2f}\") is smaller than target. "
                          f"Cropping to page's original dimensions: "
                          f"{actual_crop_width_points/POINTS_PER_INCH:.2f}\" x "
                          f"{actual_crop_height_points/POINTS_PER_INCH:.2f}\".")

                # Calculate coordinates for the new centered crop box
                new_ll_x = (original_width_points - actual_crop_width_points) / 2
                new_ll_y = (original_height_points - actual_crop_height_points) / 2
                new_ur_x = new_ll_x + actual_crop_width_points
                new_ur_y = new_ll_y + actual_crop_height_points
                
                page.cropbox = PyPDF2.generic.RectangleObject([new_ll_x, new_ll_y, new_ur_x, new_ur_y])
                
                # Optional: Set mediaBox to cropBox to remove data outside the crop area more definitively.
                # This can make the PDF smaller and prevent recovery of cropped content.
                # Consider making this behavior configurable if needed.
                # page.mediabox = page.cropbox 
                
                writer.add_page(page)

            except Exception as e_page:
                print(f"Warning: Could not process page {page_num}: {e_page}")
                # Attempt to add the original page if cropping this specific page failed
                try:
                    # Get a fresh instance of the page from the reader
                    original_page_to_add = reader.pages[i]
                    writer.add_page(original_page_to_add)
                    print(f"  Added original page {page_num} to output due to processing error.")
                except Exception as e_add_original:
                    # This page will be skipped in the output if both processing and adding original fail
                    print(f"Error: Could not add original page {page_num} after previous error: {e_add_original}")

        # Write the output PDF
        with open(output_pdf_path, "wb") as fp:
            writer.write(fp)

    except FileNotFoundError:
        print(f"Error: Input PDF file not found at '{input_pdf_path}'.")
        raise
    except PyPDF2.errors.PdfReadError as e:
        print(f"Error: Could not read PDF '{input_pdf_path}'. It might be encrypted, corrupted, or not a valid PDF: {e}")
        raise
    except IOError as e: # More specific for file writing issues
        print(f"Error: Could not write output PDF to '{output_pdf_path}': {e}")
        raise
    except Exception as e: # Catch-all for other unexpected errors
        print(f"An unexpected error occurred during PDF processing: {e}")
        raise

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description=(
            "Crops all pages of a PDF to a specified size (e.g., 9x6 inches), centered.\n"
            "If a page is smaller than the target dimensions, it is cropped to its\n"
            "original dimensions instead (preserving its content)."
        ),
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("input_pdf", help="Path to the input PDF file.")
    parser.add_argument("output_pdf", help="Path to save the cropped PDF file.")
    parser.add_argument(
        "--width", 
        type=float, 
        default=9.0, 
        help="Target width in inches for cropping (default: 9.0)."
    )
    parser.add_argument(
        "--height", 
        type=float, 
        default=6.0, 
        help="Target height in inches for cropping (default: 6.0)."
    )

    args = parser.parse_args()

    print(f"Attempting to crop '{args.input_pdf}' to '{args.output_pdf}' "
          f"with target dimensions: {args.width}\" width x {args.height}\" height.")
    
    try:
        crop_pdf_pages_centered(args.input_pdf, args.output_pdf, args.width, args.height)
        print(f"Successfully processed PDF. Cropped file saved to '{args.output_pdf}'")
    except Exception:
        # Specific error messages are already printed by crop_pdf_pages_centered before re-raising
        print("PDF cropping failed.")
        sys.exit(1)
