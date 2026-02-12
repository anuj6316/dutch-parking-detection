import cv2
import numpy as np
import os
import glob

def rotate_image(image, angle):
    (h, w) = image.shape[:2]
    (cX, cY) = (w // 2, h // 2)
    M = cv2.getRotationMatrix2D((cX, cY), angle, 1.0)
    return cv2.warpAffine(image, M, (w, h))

def detect_icons_with_rotation(image_path, templates_dir="templates", output_dir="experiments/opencv_results"):
    img_bgr = cv2.imread(image_path)
    if img_bgr is None: return
    
    img_gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    img_edges = cv2.Canny(img_gray, 50, 150)
    
    template_paths = glob.glob(os.path.join(templates_dir, "*.png"))
    os.makedirs(output_dir, exist_ok=True)

    matches_found = 0
    
    for t_path in template_paths:
        template = cv2.imread(t_path, 0)
        t_name = os.path.basename(t_path).split('.')[0]
        t_edges_base = cv2.Canny(template, 50, 150)
        
        # Multi-scale
        for scale in [0.8, 1.0, 1.2]:
            resized_t = cv2.resize(t_edges_base, None, fx=scale, fy=scale)
            
            # Multi-rotation
            for angle in range(0, 360, 45):
                rotated_t = rotate_image(resized_t, angle)
                
                if rotated_t.shape[0] > img_edges.shape[0] or rotated_t.shape[1] > img_edges.shape[1]:
                    continue

                res = cv2.matchTemplate(img_edges, rotated_t, cv2.TM_CCOEFF_NORMED)
                threshold = 0.50
                loc = np.where(res >= threshold)
                
                for pt in zip(*loc[::-1]):
                    matches_found += 1
                    w, h = rotated_t.shape[::-1]
                    cv2.rectangle(img_bgr, pt, (pt[0] + w, pt[1] + h), (0, 255, 0), 2)
                    cv2.putText(img_bgr, f"OCV:{t_name}", (pt[0], pt[1]-5), 
                                cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 0), 1)
                    break 

    if matches_found > 0:
        save_path = os.path.join(output_dir, os.path.basename(image_path))
        cv2.imwrite(save_path, img_bgr)
        print(f"Detected {matches_found} icons in {os.path.basename(image_path)}. Saved to {save_path}")

if __name__ == "__main__":
    test_images = sorted(glob.glob("obb_crops_val/*.jpg"))[:20]
    print(f"Scanning {len(test_images)} images with OpenCV Template Matching...")
    for img_p in test_images:
        detect_icons_with_rotation(img_p)
    
    # Also test on the original source image
    detect_icons_with_rotation("obb_crops/crop_28.jpg")
