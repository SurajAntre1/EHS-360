from io import BytesIO
from PIL import Image
from django.core.files.uploadedfile import InMemoryUploadedFile
import sys

def compress_image(uploaded_file, max_width=1024, max_height=1024, quality=75):
    """
    Compress uploaded image file.
    """
    # Open image with PIL
    image = Image.open(uploaded_file)
    image_format = image.format

    # Convert RGBA to RGB to avoid errors with JPEG
    if image.mode in ("RGBA", "P"):
        image = image.convert("RGB")

    # Resize maintaining aspect ratio
    image.thumbnail((max_width, max_height), Image.LANCZOS)

    # Save to BytesIO
    output = BytesIO()
    image.save(output, format=image_format, quality=quality, optimize=True)
    output.seek(0)

    # Create new Django InMemoryUploadedFile
    compressed_file = InMemoryUploadedFile(
        output, 
        uploaded_file.field_name,
        uploaded_file.name,
        uploaded_file.content_type,
        sys.getsizeof(output),
        None
    )
    return compressed_file
