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

first_file=true
for file in \
    "$VOXEL_DIR/01_Architecture.md" \
    "$VOXEL_DIR/02_Data_Structure.md" \
    "$VOXEL_DIR/03_Math.md" \
    "$VOXEL_DIR/04_FFTW.md" \
    "$VOXEL_DIR/05_Wavelet.md" \
    "$VOXEL_DIR/06_Python_Integration.md" \
    "$VOXEL_DIR/07_BuildSystem.md"
do
    if [ -f "$file" ]; then
        if [ "$first_file" = false ]; then
            echo "" >> "$TEMP_FILE"
            echo "---" >> "$TEMP_FILE"
            echo "" >> "$TEMP_FILE"
        fi
        cat "$file" >> "$TEMP_FILE"
        echo "✓ Added $(basename "$file")"
        first_file=false
    fi
done

# Generate HTML with pandoc
echo "🎨 Generating HTML with pandoc..."

pandoc "$TEMP_FILE" \
  --embed-resources \
  --standalone \
  --css "$STYLE_FILE" \
  --syntax-highlighting=tango \
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
    <nav class="sidebar">
        <div class="sidebar-title">
            <h3>📑 Contents</h3>
        </div>
        <ul class="sidebar-nav" id="sidebar-nav">
            <li><a href="#" class="sidebar-section">- Loading sections...</a></li>
        </ul>
    </nav>

    <div class="doc-header">
        <div class="container">
            <div class="header-content">
                <img src="voxel_logo.png" class="voxel-logo" alt="Voxel Library Logo">
            </div>
            <p>High-Performance C++ Multi-Dimensional Array Library with NumPy Integration</p>
        </div>
    </div>

    <div class="container">
        <div id="main-content">
EOF

# Extract the body content, preserving all styles and highlighting
sed -n '/<body>/,/<\/body>/p' "$OUTPUT_FILE" | sed '/<body>/d' | sed '/<\/body>/d' | sed '/<!\[CDATA\[/d' | sed '/\]\]>/d' >> "${OUTPUT_FILE}.tmp"

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
        // Populate sidebar navigation with collapsible sections
        function populateSidebar() {
            const sidebar = document.getElementById('sidebar-nav');
            const h1s = document.querySelectorAll('#main-content h1:not(.title)');
            
            sidebar.innerHTML = '';
            
            h1s.forEach((h1, index) => {
                if (!h1.id) {
                    h1.id = `section-${index}`;
                }
                
                // Create section group
                const sectionGroup = document.createElement('li');
                sectionGroup.className = 'sidebar-section-group';
                
                // Create toggle button
                const toggleBtn = document.createElement('button');
                toggleBtn.className = 'sidebar-section-toggle';
                toggleBtn.textContent = h1.textContent;
                toggleBtn.setAttribute('data-section-id', h1.id);
                
                // Find all h2s that follow this h1 (until next h1)
                const h2s = [];
                let nextNode = h1.nextElementSibling;
                while (nextNode && nextNode.tagName !== 'H1') {
                    if (nextNode.tagName === 'H2') {
                        h2s.push(nextNode);
                    }
                    nextNode = nextNode.nextElementSibling;
                }
                
                // Create subsections list
                const subsList = document.createElement('ul');
                subsList.className = 'sidebar-subsections collapsed';
                
                h2s.forEach((h2, subIndex) => {
                    if (!h2.id) {
                        h2.id = `subsection-${index}-${subIndex}`;
                    }
                    
                    const subLi = document.createElement('li');
                    const subLink = document.createElement('a');
                    subLink.href = `#${h2.id}`;
                    subLink.textContent = h2.textContent;
                    subLink.className = 'sidebar-link';
                    subLi.appendChild(subLink);
                    subsList.appendChild(subLi);
                });
                
                // Add toggle click handler
                toggleBtn.addEventListener('click', (e) => {
                    e.preventDefault();
                    const isExpanded = toggleBtn.classList.toggle('expanded');
                    subsList.classList.toggle('collapsed', !isExpanded);
                    
                    // Navigate to the section
                    const targetSection = document.getElementById(h1.id);
                    if (targetSection) {
                        targetSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
                    }
                });
                
                sectionGroup.appendChild(toggleBtn);
                if (h2s.length > 0) {
                    sectionGroup.appendChild(subsList);
                }
                sidebar.appendChild(sectionGroup);
            });
        }

        // Track active section as user scrolls
        function updateActiveSection() {
            const sections = document.querySelectorAll('#main-content h1:not(.title), #main-content h2');
            const scrollPos = window.scrollY + 100;
            
            sections.forEach(section => {
                const sectionTop = section.offsetTop;
                const sectionHeight = section.offsetHeight;
                
                if (scrollPos >= sectionTop && scrollPos < sectionTop + sectionHeight) {
                    const sidebarLinks = document.querySelectorAll('.sidebar-link, .sidebar-section-toggle');
                    sidebarLinks.forEach(link => link.classList.remove('active'));
                    
                    if (section.tagName === 'H1') {
                        const activeToggle = document.querySelector(`.sidebar-section-toggle[data-section-id="${section.id}"]`);
                        if (activeToggle) {
                            activeToggle.classList.add('active');
                        }
                    } else if (section.tagName === 'H2') {
                        const activeLink = document.querySelector(`.sidebar-link[href="#${section.id}"]`);
                        if (activeLink) {
                            activeLink.classList.add('active');
                        }
                    }
                }
            });
        }

        // Initialize sidebar on page load
        document.addEventListener('DOMContentLoaded', () => {
            populateSidebar();
            updateActiveSection();
        });

        // Update active section on scroll
        window.addEventListener('scroll', updateActiveSection, { passive: true });

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
