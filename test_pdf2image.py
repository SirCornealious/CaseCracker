# Update test_pdf2image.py
# Created by SuperGrok and Sir_Cornealious on X

from pdf2image import convert_from_path
pdf_path = "/Users/jared/Desktop/Python/CaseCracker/CaseCracker2.1/HelloWorld.pdf"
images = convert_from_path(pdf_path, poppler_path="/opt/homebrew/Cellar/poppler/25.04.0/bin")
for i, image in enumerate(images):
    image.save(f"test_page_{i+1}.jpg", "JPEG")
print(f"Converted {len(images)} pages")