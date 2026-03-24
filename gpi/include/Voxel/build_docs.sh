#!/bin/bash

# Voxel Documentation HTML Generator
# This script combines all .md files and generates a single HTML page with styling

set -e

VOXEL_DIR="/Users/gkrishnamoo3/Documents/SW/gpi_source/gpi/include/Voxel"
OUTPUT_FILE="$VOXEL_DIR/voxel_documentation.html"
TEMP_FILE="/tmp/voxel_combined.md"
STYLE_FILE="$VOXEL_DIR/style.css"

echo "🔨 Building Voxel Documentation HTML..."

# Clear temp file
> "$TEMP_FILE"

# Combine markdown files in order
echo "📝 Combining markdown files..."

for file in \
    "$VOXEL_DIR/README.md" \
    "$VOXEL_DIR/01_Architecture.md" \
    "$VOXEL_DIR/02_Data_Structure.md" \
    "$VOXEL_DIR/03_Math.md" \
    "$VOXEL_DIR/04_FFTW.md" \
    "$VOXEL_DIR/05_Wavelet.md" \
    "$VOXEL_DIR/06_Python_Integration.md" \
    "$VOXEL_DIR/07_BuildSystem.md"
do
    if [ -f "$file" ]; then
        echo "" >> "$TEMP_FILE"
        echo "---" >> "$TEMP_FILE"
        echo "" >> "$TEMP_FILE"
        cat "$file" >> "$TEMP_FILE"
        echo "✓ Added $(basename "$file")"
    fi
done

# Generate HTML with pandoc
echo "🎨 Generating HTML with pandoc..."

pandoc "$TEMP_FILE" \
  --self-contained \
  --css "$STYLE_FILE" \
  --toc \
  --toc-depth=3 \
  --highlight-style=tango \
  --number-sections \
  --metadata title="Voxel Library: Multi-Dimensional Array Library" \
  --metadata author="GPI Source" \
  -f markdown \
  -t html5 \
  -o "$OUTPUT_FILE"

# Add header and footer
echo "✨ Enhancing HTML..."

# Create final HTML with improved structure
cat > "${OUTPUT_FILE}.tmp" << 'EOF'
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="description" content="Voxel - A high-performance C++ multi-dimensional array library with NumPy integration">
    <meta name="author" content="GPI Source">
    <title>Voxel Library Documentation</title>
    <style>
EOF

cat "$STYLE_FILE" >> "${OUTPUT_FILE}.tmp"

cat >> "${OUTPUT_FILE}.tmp" << 'EOF'
    </style>
</head>
<body>
    <div class="doc-header">
        <div class="container">
            <h1>📊 Voxel Library</h1>
            <p>High-Performance C++ Multi-Dimensional Array Library with NumPy Integration</p>
        </div>
    </div>

    <div class="container">
        <div id="main-content">
EOF

# Extract the body content from the pandoc-generated HTML
sed -n '/<body>/,/<\/body>/p' "$OUTPUT_FILE" | sed '/<body>/d' | sed '/<\/body>/d' >> "${OUTPUT_FILE}.tmp"

cat >> "${OUTPUT_FILE}.tmp" << 'EOF'
        </div>

        <div class="doc-footer">
            <p><strong>Voxel Library Documentation</strong></p>
            <p>A scientific computing library optimized for computational imaging and signal processing</p>
            <p>© 2024-2026 GPI Source | <a href="https://github.com">GitHub</a></p>
        </div>
    </div>

    <button id="back-to-top" title="Go to top">↑</button>

    <script>
        // Back to top button functionality
        const backToTopBtn = document.getElementById('back-to-top');
        
        window.addEventListener('scroll', () => {
            if (window.pageYOffset > 300) {
                backToTopBtn.classList.add('show');
            } else {
                backToTopBtn.classList.remove('show');
            }
        });

        backToTopBtn.addEventListener('click', () => {
            window.scrollTo({ top: 0, behavior: 'smooth' });
        });

        // Enhance code blocks with line numbers (optional)
        document.querySelectorAll('pre > code').forEach((block) => {
            block.className += ' language-cpp';
        });
    </script>
</body>
</html>
EOF

# Replace original with enhanced version
mv "${OUTPUT_FILE}.tmp" "$OUTPUT_FILE"

# Clean up
rm -f "$TEMP_FILE"

# Get file size
FILESIZE=$(du -h "$OUTPUT_FILE" | cut -f1)

echo ""
echo "✅ Success! HTML documentation generated:"
echo "   📄 File: $OUTPUT_FILE"
echo "   📊 Size: $FILESIZE"
echo ""
echo "🌐 Open in browser: open '$OUTPUT_FILE'"
