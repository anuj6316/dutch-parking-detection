import fitz  # PyMuPDF
import os

pdf_path = "/home/mindmap/Desktop/dutch-parking-detection/experiments/TEST_K3-a-2.pdf"
output_dir = "images"
dpi = 50

os.makedirs(output_dir, exist_ok=True)

doc = fitz.open(pdf_path)

# DPI to zoom factor
zoom = dpi / 72  # 72 is default PDF DPI
mat = fitz.Matrix(zoom, zoom)

for page_num in range(len(doc)):
    page = doc[page_num]
    pix = page.get_pixmap(matrix=mat)
    output_path = os.path.join(output_dir, f"page_{page_num+1}.png")
    pix.save(output_path)

doc.close()
