# Photo Enhancer Script

A comprehensive Python-based photo enhancement tool designed to automatically improve portrait photographs through various image processing techniques.

## Features

This script applies the following enhancements to portrait photos:

1. **Auto-crop** - Removes 10% from the top of the image (useful for eliminating bright ceiling lights)
2. **White Balance Adjustment** - Reduces warm (yellow) tones using Gray World algorithm
3. **Contrast Enhancement** - Applies CLAHE to enhance facial features
4. **Facial Landmark Detection** - Uses MediaPipe to detect eyes, hair, and face regions
5. **Local Sharpening** - Sharpens eyes and hair for better detail
6. **Skin Smoothing** - Applies bilateral filtering for subtle texture reduction
7. **Background Blur** - Creates depth-of-field effect by blurring and darkening background
8. **Eye Enhancement** - Brightens and saturates eyes subtly

## Installation

### On CachyOS (Arch-based Linux)

```bash
# Install system packages
sudo pacman -S python-opencv python-numpy python-pillow

# Install additional Python packages (with updated secure versions)
pip install --upgrade opencv-python>=4.8.1.78 pillow>=10.2.0 mediapipe scikit-image
```

**Note**: Ensure you use the minimum versions specified to avoid known security vulnerabilities.

### On other systems

```bash
pip install -r photo_enhancer_requirements.txt
```

Or install packages individually:

```bash
pip install opencv-python>=4.8.1.78 numpy pillow>=10.2.0 mediapipe scikit-image
```

## Usage

### Process a Single Image

```bash
python photo_enhancer.py input.jpg
```

This will create `input_enhanced.jpg` in the same directory.

### Specify Output Path

```bash
python photo_enhancer.py input.jpg -o /path/to/output.jpg
```

### Batch Process All JPG Files in a Directory

```bash
python photo_enhancer.py /path/to/photos/
```

This will process all `.jpg`, `.jpeg`, `.JPG`, and `.JPEG` files in the directory and create enhanced versions with `_enhanced` suffix.

### Command-Line Options

```
photo_enhancer.py [-h] [-o OUTPUT] input

Positional arguments:
  input                 Input image file or directory containing JPG files

Optional arguments:
  -h, --help            Show this help message and exit
  -o OUTPUT, --output OUTPUT
                        Output file path (only for single image processing)
```

## Technical Details

### Libraries Used

- **OpenCV** (`opencv-python`) - Core image processing operations
- **NumPy** - Numerical computations and array operations
- **Pillow** - Additional image handling capabilities
- **MediaPipe** - Facial landmark detection (Google's ML solution)
- **scikit-image** - Advanced image processing algorithms

### Processing Pipeline

1. **Image Loading** - Reads image using OpenCV
2. **Auto-crop** - Removes top 10% of pixels
3. **White Balance** - Adjusts LAB color space to neutralize color cast
4. **Contrast** - Uses CLAHE (Contrast Limited Adaptive Histogram Equalization)
5. **Face Detection** - MediaPipe Face Mesh identifies facial landmarks
6. **Selective Sharpening** - Unsharp mask applied to eyes and hair regions
7. **Skin Smoothing** - Edge-preserving bilateral filter
8. **Background Processing** - Gaussian blur and darkening for depth effect
9. **Eye Enhancement** - HSV color space adjustments for brightness and saturation
10. **Output** - High-quality JPEG saved (95% quality)

### Fallback Behavior

If no face is detected in an image, the script will:
- Apply global sharpening instead of localized sharpening
- Use edge-based segmentation for background blur
- Skip eye-specific enhancements

This ensures the script can still improve non-portrait images.

## Examples

### Before and After Comparison

The script is particularly effective for:
- Indoor portraits with ceiling lights
- Photos with yellow/warm color casts
- Images needing skin texture improvement
- Photos where the subject needs to stand out from background

### Performance

Processing time varies based on image size:
- Small images (< 1MP): ~2-3 seconds
- Medium images (1-5MP): ~5-8 seconds
- Large images (> 5MP): ~10-15 seconds

## Troubleshooting

### MediaPipe Installation Issues

If you encounter issues installing MediaPipe on CachyOS:

```bash
# Try installing with pip in user space
pip install --user mediapipe
```

### Memory Issues with Large Images

For very large images (> 20MP), consider resizing before processing:

```bash
# Using ImageMagick
convert large_image.jpg -resize 50% medium_image.jpg
python photo_enhancer.py medium_image.jpg
```

### No Face Detected

If the script reports "No face detected," ensure:
- The subject is clearly visible and well-lit
- The face is not too small in the frame
- The photo is not overly dark or overexposed

## Advanced Usage

### Modifying Enhancement Strength

You can edit the script to adjust enhancement parameters:

- **Crop percentage**: Line with `auto_crop_top(image, crop_percentage=10)`
- **Contrast strength**: CLAHE `clipLimit` parameter
- **Sharpening strength**: `strength=1.3` in `sharpen_region()`
- **Skin smoothing**: `strength=15` in `apply_skin_smoothing()`
- **Background darkness**: `0.7` weight in `darken_blur_background()`

### Using with Other Tools

The script can be integrated into larger workflows:

```bash
# Process and then optimize file size
python photo_enhancer.py input.jpg
optipng input_enhanced.jpg
```

## License

This script is provided as part of the Czkawka project and follows the same MIT license.

## Credits

- Uses Google's MediaPipe for facial landmark detection
- OpenCV for image processing operations
- Bilateral filtering concept for skin smoothing

## Contributing

Suggestions for improvements:
- Integration with U²-Net for better subject segmentation
- GPU acceleration for batch processing
- Support for RAW image formats
- Additional enhancement presets (studio, outdoor, etc.)
