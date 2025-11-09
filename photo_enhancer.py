#!/usr/bin/env python3
"""
Photo Enhancement Script for CachyOS

This script applies various image enhancements to portrait photographs:
- Auto-crop to remove ceiling light
- White balance adjustment
- Contrast enhancement
- Local sharpening (eyes and hair)
- Skin smoothing
- Background blur (depth of field simulation)
- Eye enhancement

Requirements:
    pip install -r photo_enhancer_requirements.txt
    
    Or:
    pip install opencv-python>=4.8.1.78 numpy pillow>=10.2.0 mediapipe scikit-image

Usage:
    # Single image
    python photo_enhancer.py input.jpg
    
    # Batch process all JPGs in a directory
    python photo_enhancer.py /path/to/folder/
"""

import os
import sys
import argparse
from pathlib import Path
import cv2
import numpy as np
from PIL import Image
import mediapipe as mp

# Initialize MediaPipe Face Mesh for facial landmark detection
mp_face_mesh = mp.solutions.face_mesh
face_mesh = mp_face_mesh.FaceMesh(
    static_image_mode=True,
    max_num_faces=1,
    refine_landmarks=True,
    min_detection_confidence=0.5
)


def auto_crop_top(image, crop_percentage=10):
    """
    Remove a percentage from the top of the image to eliminate ceiling light.
    
    Args:
        image: Input image (numpy array)
        crop_percentage: Percentage to crop from top (default: 10%)
    
    Returns:
        Cropped image
    """
    height = image.shape[0]
    crop_pixels = int(height * crop_percentage / 100)
    return image[crop_pixels:, :]


def adjust_white_balance(image):
    """
    Adjust white balance to reduce warm (yellow) tones.
    Uses the Gray World assumption for neutral white point.
    
    Args:
        image: Input image in BGR format
    
    Returns:
        White-balanced image
    """
    result = cv2.cvtColor(image, cv2.COLOR_BGR2LAB).astype("float32")
    
    # Compute average LAB values
    avg_a = np.average(result[:, :, 1])
    avg_b = np.average(result[:, :, 2])
    
    # Adjust the image to neutralize color cast
    result[:, :, 1] = result[:, :, 1] - ((avg_a - 128) * (result[:, :, 0] / 255.0) * 1.1)
    result[:, :, 2] = result[:, :, 2] - ((avg_b - 128) * (result[:, :, 0] / 255.0) * 1.1)
    
    result = np.clip(result, 0, 255)
    result = cv2.cvtColor(result.astype("uint8"), cv2.COLOR_LAB2BGR)
    
    return result


def increase_contrast(image, alpha=1.2):
    """
    Increase contrast slightly to enhance facial features.
    
    Args:
        image: Input image
        alpha: Contrast control (1.0-3.0, default: 1.2)
    
    Returns:
        Contrast-enhanced image
    """
    # Convert to LAB color space
    lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    
    # Apply CLAHE (Contrast Limited Adaptive Histogram Equalization) to L channel
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    l = clahe.apply(l)
    
    # Merge channels
    lab = cv2.merge([l, a, b])
    enhanced = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)
    
    return enhanced


def detect_facial_landmarks(image):
    """
    Detect facial landmarks using MediaPipe Face Mesh.
    
    Args:
        image: Input image in BGR format
    
    Returns:
        Dictionary with landmark regions (eyes, hair) or None if no face detected
    """
    # Convert BGR to RGB
    image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    results = face_mesh.process(image_rgb)
    
    if not results.multi_face_landmarks:
        return None
    
    h, w = image.shape[:2]
    landmarks = results.multi_face_landmarks[0]
    
    # Define eye regions (approximate indices for left and right eyes)
    left_eye_indices = [33, 160, 158, 133, 153, 144, 145, 163]
    right_eye_indices = [362, 385, 387, 263, 373, 380, 374, 390]
    
    # Get eye coordinates
    left_eye_points = []
    right_eye_points = []
    
    for idx in left_eye_indices:
        landmark = landmarks.landmark[idx]
        left_eye_points.append((int(landmark.x * w), int(landmark.y * h)))
    
    for idx in right_eye_indices:
        landmark = landmarks.landmark[idx]
        right_eye_points.append((int(landmark.x * w), int(landmark.y * h)))
    
    # Estimate hair region (top 30% of face)
    face_top = min([landmarks.landmark[i].y for i in range(len(landmarks.landmark))])
    forehead_y = int(face_top * h)
    hair_region = (0, max(0, forehead_y - int(h * 0.15)), w, forehead_y)
    
    return {
        'left_eye': left_eye_points,
        'right_eye': right_eye_points,
        'hair_region': hair_region
    }


def sharpen_region(image, mask, strength=1.5):
    """
    Apply sharpening to specific regions using an unsharp mask.
    
    Args:
        image: Input image
        mask: Binary mask of regions to sharpen
        strength: Sharpening strength (default: 1.5)
    
    Returns:
        Sharpened image
    """
    # Create Gaussian blur
    blurred = cv2.GaussianBlur(image, (0, 0), 3)
    
    # Unsharp mask
    sharpened = cv2.addWeighted(image, 1.0 + strength, blurred, -strength, 0)
    
    # Apply sharpening only to masked regions
    result = image.copy()
    result[mask > 0] = sharpened[mask > 0]
    
    return result


def apply_local_sharpening(image, landmarks):
    """
    Apply local sharpening to eyes and hair regions.
    
    Args:
        image: Input image
        landmarks: Dictionary with facial landmark regions
    
    Returns:
        Image with sharpened eyes and hair
    """
    if landmarks is None:
        # If no face detected, apply mild global sharpening
        kernel = np.array([[-1, -1, -1],
                          [-1,  9, -1],
                          [-1, -1, -1]]) / 9
        return cv2.filter2D(image, -1, kernel)
    
    h, w = image.shape[:2]
    mask = np.zeros((h, w), dtype=np.uint8)
    
    # Create masks for eye regions
    left_eye_points = np.array(landmarks['left_eye'], dtype=np.int32)
    right_eye_points = np.array(landmarks['right_eye'], dtype=np.int32)
    
    # Expand eye regions for better effect
    cv2.fillConvexPoly(mask, left_eye_points, 255)
    cv2.fillConvexPoly(mask, right_eye_points, 255)
    
    # Dilate eye masks to include surrounding area
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (30, 30))
    mask = cv2.dilate(mask, kernel)
    
    # Add hair region to mask
    x1, y1, x2, y2 = landmarks['hair_region']
    mask[y1:y2, x1:x2] = 255
    
    # Apply sharpening
    return sharpen_region(image, mask, strength=1.3)


def apply_skin_smoothing(image, landmarks, strength=15):
    """
    Apply subtle skin smoothing using bilateral filter.
    Preserves edges while smoothing skin texture.
    
    Args:
        image: Input image
        landmarks: Dictionary with facial landmark regions
        strength: Smoothing strength (default: 15)
    
    Returns:
        Smoothed image
    """
    if landmarks is None:
        # Apply mild smoothing globally if no face detected
        return cv2.bilateralFilter(image, 9, 20, 20)
    
    # Apply bilateral filter for edge-preserving smoothing
    smoothed = cv2.bilateralFilter(image, strength, strength * 2, strength * 2)
    
    # Blend smoothed with original (70% smoothed, 30% original)
    result = cv2.addWeighted(smoothed, 0.7, image, 0.3, 0)
    
    return result


def segment_subject(image):
    """
    Simple subject segmentation using edge detection and morphology.
    This is a basic implementation. For better results, consider using U^2-Net or similar.
    
    Args:
        image: Input image
    
    Returns:
        Binary mask (255 for subject, 0 for background)
    """
    # Convert to grayscale
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    # Apply edge detection
    edges = cv2.Canny(gray, 50, 150)
    
    # Dilate edges to create connected regions
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    dilated = cv2.dilate(edges, kernel, iterations=2)
    
    # Find contours
    contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    # Create mask with the largest contour (assumed to be subject)
    mask = np.zeros(gray.shape, dtype=np.uint8)
    if contours:
        largest_contour = max(contours, key=cv2.contourArea)
        cv2.drawContours(mask, [largest_contour], -1, 255, -1)
        
        # Fill holes
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (20, 20))
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
    
    # Smooth mask edges
    mask = cv2.GaussianBlur(mask, (21, 21), 0)
    
    return mask


def darken_blur_background(image, landmarks):
    """
    Darken and blur the background to emphasize the subject (depth of field effect).
    
    Args:
        image: Input image
        landmarks: Dictionary with facial landmark regions
    
    Returns:
        Image with blurred and darkened background
    """
    # Create subject mask
    if landmarks is not None:
        # Use face landmarks to create a better mask
        h, w = image.shape[:2]
        mask = np.zeros((h, w), dtype=np.uint8)
        
        # Create ellipse around face region
        face_points = np.array(landmarks['left_eye'] + landmarks['right_eye'])
        if len(face_points) > 0:
            center, axes, angle = cv2.fitEllipse(face_points)
            # Expand ellipse to include full subject
            axes = (int(axes[0] * 2.5), int(axes[1] * 3))
            cv2.ellipse(mask, (int(center[0]), int(center[1])), axes, angle, 0, 360, 255, -1)
    else:
        # Fallback: simple center-focused mask
        mask = segment_subject(image)
    
    # Blur background
    blurred = cv2.GaussianBlur(image, (21, 21), 0)
    
    # Darken background
    darkened = cv2.addWeighted(blurred, 0.7, np.zeros_like(blurred), 0, 0)
    
    # Create smooth transition mask
    mask_float = mask.astype(float) / 255.0
    mask_float = cv2.GaussianBlur(mask_float, (51, 51), 0)
    mask_3ch = cv2.merge([mask_float, mask_float, mask_float])
    
    # Blend subject with darkened/blurred background
    result = (image * mask_3ch + darkened * (1 - mask_3ch)).astype(np.uint8)
    
    return result


def enhance_eyes(image, landmarks):
    """
    Enhance eye brightness and saturation subtly.
    
    Args:
        image: Input image
        landmarks: Dictionary with facial landmark regions
    
    Returns:
        Image with enhanced eyes
    """
    if landmarks is None:
        return image
    
    h, w = image.shape[:2]
    result = image.copy()
    
    # Create mask for eyes
    mask = np.zeros((h, w), dtype=np.uint8)
    
    left_eye_points = np.array(landmarks['left_eye'], dtype=np.int32)
    right_eye_points = np.array(landmarks['right_eye'], dtype=np.int32)
    
    cv2.fillConvexPoly(mask, left_eye_points, 255)
    cv2.fillConvexPoly(mask, right_eye_points, 255)
    
    # Dilate to include iris area
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (15, 15))
    mask = cv2.dilate(mask, kernel)
    mask = cv2.GaussianBlur(mask, (11, 11), 0)
    
    # Convert to HSV for brightness and saturation adjustment
    hsv = cv2.cvtColor(result, cv2.COLOR_BGR2HSV).astype(float)
    
    # Create mask for blending
    mask_3ch = cv2.merge([mask, mask, mask]).astype(float) / 255.0
    
    # Increase brightness (V channel) and saturation (S channel) for eyes
    hsv[:, :, 1] = hsv[:, :, 1] + (20 * mask_3ch[:, :, 0])  # Saturation
    hsv[:, :, 2] = hsv[:, :, 2] + (25 * mask_3ch[:, :, 0])  # Brightness
    
    # Clip values
    hsv = np.clip(hsv, 0, 255)
    
    result = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)
    
    return result


def enhance_photo(input_path, output_path=None):
    """
    Apply all enhancements to a photo.
    
    Args:
        input_path: Path to input image
        output_path: Path to save output (default: input_name_enhanced.jpg)
    
    Returns:
        True if successful, False otherwise
    """
    try:
        # Read image
        print(f"Processing: {input_path}")
        image = cv2.imread(input_path)
        
        if image is None:
            print(f"Error: Could not read image {input_path}")
            return False
        
        # 1. Auto-crop top 10%
        print("  - Cropping top 10%...")
        image = auto_crop_top(image, crop_percentage=10)
        
        # 2. Adjust white balance
        print("  - Adjusting white balance...")
        image = adjust_white_balance(image)
        
        # 3. Increase contrast
        print("  - Enhancing contrast...")
        image = increase_contrast(image)
        
        # 4. Detect facial landmarks
        print("  - Detecting facial landmarks...")
        landmarks = detect_facial_landmarks(image)
        
        if landmarks:
            print("    ✓ Face detected")
        else:
            print("    ! No face detected, applying global enhancements")
        
        # 5. Apply local sharpening
        print("  - Sharpening eyes and hair...")
        image = apply_local_sharpening(image, landmarks)
        
        # 6. Apply skin smoothing
        print("  - Smoothing skin...")
        image = apply_skin_smoothing(image, landmarks)
        
        # 7. Darken and blur background
        print("  - Creating depth of field effect...")
        image = darken_blur_background(image, landmarks)
        
        # 8. Enhance eyes
        print("  - Enhancing eyes...")
        image = enhance_eyes(image, landmarks)
        
        # Determine output path
        if output_path is None:
            input_file = Path(input_path)
            output_path = input_file.parent / f"{input_file.stem}_enhanced{input_file.suffix}"
        
        # Save the output
        print(f"  - Saving to: {output_path}")
        cv2.imwrite(str(output_path), image, [cv2.IMWRITE_JPEG_QUALITY, 95])
        
        print(f"✓ Successfully enhanced: {output_path}\n")
        return True
        
    except Exception as e:
        print(f"Error processing {input_path}: {str(e)}")
        return False


def batch_process(directory):
    """
    Process all JPG files in a directory.
    
    Args:
        directory: Path to directory containing images
    """
    directory = Path(directory)
    
    if not directory.is_dir():
        print(f"Error: {directory} is not a valid directory")
        return
    
    # Find all JPG files
    jpg_files = list(directory.glob("*.jpg")) + list(directory.glob("*.JPG")) + \
                list(directory.glob("*.jpeg")) + list(directory.glob("*.JPEG"))
    
    if not jpg_files:
        print(f"No JPG files found in {directory}")
        return
    
    print(f"Found {len(jpg_files)} images to process\n")
    
    success_count = 0
    for jpg_file in jpg_files:
        if enhance_photo(str(jpg_file)):
            success_count += 1
    
    print(f"\n{'='*50}")
    print(f"Batch processing complete!")
    print(f"Successfully processed: {success_count}/{len(jpg_files)} images")
    print(f"{'='*50}")


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description="Enhance portrait photographs with automatic adjustments",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Process a single image
  python photo_enhancer.py portrait.jpg
  
  # Process all images in a directory
  python photo_enhancer.py /path/to/photos/
  
  # Specify output path
  python photo_enhancer.py input.jpg -o output.jpg

Requirements:
  Install required packages with:
  pip install -r photo_enhancer_requirements.txt
  
  Or individually:
  pip install opencv-python>=4.8.1.78 numpy pillow>=10.2.0 mediapipe scikit-image
  
  Or on CachyOS (Arch-based):
  sudo pacman -S python-opencv python-numpy python-pillow
  pip install --upgrade opencv-python>=4.8.1.78 pillow>=10.2.0 mediapipe scikit-image
        """
    )
    
    parser.add_argument(
        'input',
        help='Input image file or directory containing JPG files'
    )
    
    parser.add_argument(
        '-o', '--output',
        help='Output file path (only for single image processing)',
        default=None
    )
    
    args = parser.parse_args()
    
    input_path = Path(args.input)
    
    # Check if input is a directory or file
    if input_path.is_dir():
        batch_process(input_path)
    elif input_path.is_file():
        enhance_photo(str(input_path), args.output)
    else:
        print(f"Error: {args.input} is not a valid file or directory")
        sys.exit(1)


if __name__ == "__main__":
    main()
