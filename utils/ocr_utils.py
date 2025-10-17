import pytesseract
from PIL import Image

# Optional: Set Tesseract executable path (Windows)
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

def extract_text_from_image(image_path):
    """
    Extract text from a scanned image using OCR.
    :param image_path: Path to the scanned image file.
    :return: Extracted text as a string.
    """
    print(image_path)
    try:
        # Open the image file
        img = Image.open(image_path)

        # Perform OCR on the image
        extracted_text = pytesseract.image_to_string(img)

        return extracted_text
    except Exception as e:
        print(f"Error processing image: {e}")
        return None