import cv2
import os

def extract_template(image_path, x, y, w, h, template_name):
    img = cv2.imread(image_path)
    if img is None:
        print(f"Error: Could not load {image_path}")
        return

    # Crop the icon using integer coordinates
    template = img[int(y):int(y+h), int(x):int(x+w)]
    
    os.makedirs("templates", exist_ok=True)
    save_path = f"templates/{template_name}.png"
    cv2.imwrite(save_path, template)
    print(f"Correct template saved to {save_path}")

if __name__ == "__main__":
    image_to_use = "obb_crops/crop_28.jpg"
    
    # Using the second detection from crop_28.jpg
    # Box: [100.8, 17.54, 143.65, 71.33] -> x=100, y=17, w=43, h=54
    extract_template(image_to_use, x=100, y=17, w=44, h=55, template_name="wheelchair")
