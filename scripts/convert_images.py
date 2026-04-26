#!/usr/bin/env python3
"""Convert all images in a directory (recursively) to a different format.

This script finds all image files (png, jpg, jpeg, webp, svg) in a directory
and converts them to the specified output format using Plotly's kaleido engine.

Usage:
    python convert_images.py <directory> <output_format> [--delete-originals] [--dry-run]

Examples:
    # Convert all images in ~/negmas/app to webp
    python convert_images.py ~/negmas/app webp

    # Convert and delete originals
    python convert_images.py ~/negmas/app webp --delete-originals

    # Dry run to see what would be converted
    python convert_images.py ~/negmas/app webp --dry-run

Supported formats:
    - webp (best compression, recommended)
    - png
    - jpg/jpeg
    - svg (vector format)
"""

import argparse
import sys
from pathlib import Path

from PIL import Image


# Supported input formats
INPUT_FORMATS = {".png", ".jpg", ".jpeg", ".webp", ".svg", ".bmp", ".gif", ".tiff"}

# Supported output formats
OUTPUT_FORMATS = {"webp", "png", "jpg", "jpeg", "svg"}


def find_images(directory: Path) -> list[Path]:
    """Find all image files in directory recursively.

    Args:
        directory: Root directory to search.

    Returns:
        List of image file paths.
    """
    images = []
    for ext in INPUT_FORMATS:
        images.extend(directory.rglob(f"*{ext}"))
    return sorted(images)


def convert_image(
    image_path: Path,
    output_format: str,
    delete_original: bool = False,
    dry_run: bool = False,
) -> bool:
    """Convert an image to a different format.

    Args:
        image_path: Path to input image.
        output_format: Output format (webp, png, jpg, svg).
        delete_original: Whether to delete the original file.
        dry_run: If True, only print what would be done.

    Returns:
        True if successful, False otherwise.
    """
    # Skip if already in target format
    if image_path.suffix.lower() == f".{output_format}":
        return True

    output_path = image_path.with_suffix(f".{output_format}")

    if dry_run:
        print(f"  Would convert: {image_path} -> {output_path}")
        if delete_original:
            print(f"  Would delete: {image_path}")
        return True

    try:
        # Load and convert image
        img = Image.open(image_path)

        # Handle transparency for JPEG
        if output_format in ("jpg", "jpeg") and img.mode in ("RGBA", "LA", "P"):
            # Convert to RGB, replacing transparency with white
            background = Image.new("RGB", img.size, (255, 255, 255))
            if img.mode == "P":
                img = img.convert("RGBA")
            background.paste(img, mask=img.split()[-1] if img.mode == "RGBA" else None)
            img = background

        # Save in new format
        save_kwargs = {}
        if output_format == "webp":
            save_kwargs["quality"] = 90  # High quality WebP
            save_kwargs["method"] = 6  # Better compression
        elif output_format in ("jpg", "jpeg"):
            save_kwargs["quality"] = 90
            save_kwargs["optimize"] = True
        elif output_format == "png":
            save_kwargs["optimize"] = True

        img.save(output_path, **save_kwargs)

        # Delete original if requested
        if delete_original and output_path != image_path:
            image_path.unlink()
            print(f"  ✓ Converted and deleted: {image_path} -> {output_path}")
        else:
            print(f"  ✓ Converted: {image_path} -> {output_path}")

        return True

    except Exception as e:
        print(f"  ✗ Error converting {image_path}: {e}")
        return False


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Convert all images in a directory to a different format",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    parser.add_argument(
        "directory",
        type=str,
        help="Directory to search for images",
    )

    parser.add_argument(
        "format",
        type=str,
        choices=list(OUTPUT_FORMATS),
        help="Output format",
    )

    parser.add_argument(
        "--delete-originals",
        action="store_true",
        help="Delete original files after conversion",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without actually converting",
    )

    args = parser.parse_args()

    # Validate directory
    directory = Path(args.directory).expanduser().resolve()
    if not directory.exists():
        print(f"Error: Directory does not exist: {directory}")
        sys.exit(1)

    if not directory.is_dir():
        print(f"Error: Not a directory: {directory}")
        sys.exit(1)

    # Find images
    print(f"Searching for images in: {directory}")
    images = find_images(directory)

    if not images:
        print("No images found.")
        return

    # Filter out images already in target format
    images_to_convert = [
        img for img in images if img.suffix.lower() != f".{args.format}"
    ]

    if not images_to_convert:
        print(f"All {len(images)} images are already in {args.format} format.")
        return

    print(f"\nFound {len(images)} images total")
    print(f"{len(images_to_convert)} images to convert to {args.format}")
    print(
        f"{len(images) - len(images_to_convert)} images already in {args.format} format"
    )

    if args.dry_run:
        print("\n[DRY RUN MODE - No files will be modified]\n")
    elif args.delete_originals:
        print("\n[WARNING] Original files will be DELETED after conversion")
        response = input("Continue? (yes/no): ")
        if response.lower() not in ("yes", "y"):
            print("Aborted.")
            return

    print()

    # Convert images
    success_count = 0
    for i, image_path in enumerate(images_to_convert, 1):
        print(f"[{i}/{len(images_to_convert)}] {image_path.name}")
        if convert_image(image_path, args.format, args.delete_originals, args.dry_run):
            success_count += 1

    # Summary
    print(f"\n{'=' * 60}")
    if args.dry_run:
        print(
            f"Dry run complete: {success_count}/{len(images_to_convert)} images would be converted"
        )
    else:
        print(
            f"Conversion complete: {success_count}/{len(images_to_convert)} images converted successfully"
        )
        if args.delete_originals:
            print(f"Deleted {success_count} original files")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
