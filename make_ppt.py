"""Generate GPI 2.0 improvements presentation."""
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.util import Inches, Pt

# ── colour palette ────────────────────────────────────────────────────────────
BG       = RGBColor(0x1e, 0x1e, 0x2e)   # near-black blue
ACCENT   = RGBColor(0x89, 0xb4, 0xfa)   # soft blue
HEADING  = RGBColor(0xcd, 0xd6, 0xf4)   # light lavender
BODY     = RGBColor(0xba, 0xc2, 0xde)   # muted white
DIM      = RGBColor(0x58, 0x5b, 0x70)   # dark grey divider
GREEN    = RGBColor(0xa6, 0xe3, 0xa1)
YELLOW   = RGBColor(0xf9, 0xe2, 0xaf)
RED      = RGBColor(0xf3, 0x8b, 0xa8)
PEACH    = RGBColor(0xfa, 0xb3, 0x87)

SLIDE_W = Inches(13.33)
SLIDE_H = Inches(7.5)

prs = Presentation()
prs.slide_width  = SLIDE_W
prs.slide_height = SLIDE_H

blank_layout = prs.slide_layouts[6]   # completely blank


# ── helpers ───────────────────────────────────────────────────────────────────

def add_rect(slide, l, t, w, h, fill=None, line=None):
    shape = slide.shapes.add_shape(1, Inches(l), Inches(t), Inches(w), Inches(h))
    if fill:
        shape.fill.solid()
        shape.fill.fore_color.rgb = fill
    else:
        shape.fill.background()
    if line:
        shape.line.color.rgb = line
        shape.line.width = Pt(0.75)
    else:
        shape.line.fill.background()
    return shape


def add_text(slide, text, l, t, w, h,
             size=18, bold=False, color=BODY, align=PP_ALIGN.LEFT,
             wrap=True, italic=False):
    txbox = slide.shapes.add_textbox(Inches(l), Inches(t), Inches(w), Inches(h))
    txbox.word_wrap = wrap
    tf = txbox.text_frame
    tf.word_wrap = wrap
    p = tf.paragraphs[0]
    p.alignment = align
    run = p.add_run()
    run.text = text
    run.font.size  = Pt(size)
    run.font.bold  = bold
    run.font.color.rgb = color
    run.font.italic = italic
    return txbox


def set_bg(slide, color=BG):
    bg = slide.background
    fill = bg.fill
    fill.solid()
    fill.fore_color.rgb = color


def bullet_block(slide, items, l, t, w, h, size=15, dot_color=ACCENT,
                 text_color=BODY, indent=0.22):
    """Draw a list of (bullet, text) or plain strings as bullet points."""
    txbox = slide.shapes.add_textbox(Inches(l), Inches(t), Inches(w), Inches(h))
    txbox.word_wrap = True
    tf = txbox.text_frame
    tf.word_wrap = True
    first = True
    for item in items:
        if isinstance(item, tuple):
            dot, line = item
        else:
            dot, line = "•", item
        p = tf.paragraphs[0] if first else tf.add_paragraph()
        first = False
        p.alignment = PP_ALIGN.LEFT
        # dot
        r1 = p.add_run()
        r1.text = dot + "  "
        r1.font.size  = Pt(size)
        r1.font.color.rgb = dot_color
        r1.font.bold  = True
        # text
        r2 = p.add_run()
        r2.text = line
        r2.font.size  = Pt(size)
        r2.font.color.rgb = text_color
        # spacing
        p.space_after = Pt(4)


def section_tag(slide, label, color=ACCENT, l=0.3, t=0.18):
    add_rect(slide, l, t, 1.7, 0.28, fill=color)
    add_text(slide, label, l + 0.07, t + 0.02, 1.56, 0.26,
             size=10, bold=True, color=BG, align=PP_ALIGN.LEFT)


# ═══════════════════════════════════════════════════════════════════════════════
# SLIDE 1 — Title
# ═══════════════════════════════════════════════════════════════════════════════
s = prs.slides.add_slide(blank_layout)
set_bg(s)

# left accent bar
add_rect(s, 0, 0, 0.08, 7.5, fill=ACCENT)

# big title
add_text(s, "GPI 2.0", 0.45, 1.6, 8, 1.5,
         size=72, bold=True, color=HEADING, align=PP_ALIGN.LEFT)

# subtitle
add_text(s, "Major Improvements  ·  v1.4.5 → v2.0",
         0.45, 3.15, 9, 0.6,
         size=24, bold=False, color=ACCENT, align=PP_ALIGN.LEFT)

# divider line
add_rect(s, 0.45, 3.85, 9.5, 0.04, fill=DIM)

# highlights
highlights = [
    ("Python 3.13  +  PyQt6  +  Windows",  HEADING),
    ("New C++ compute engine  (Voxel / pybind11)", BODY),
    ("Redesigned process execution & memory architecture", BODY),
    ("165 commits  ·  235 files  ·  +67 k lines", DIM),
]
y = 4.05
for txt, col in highlights:
    add_text(s, txt, 0.65, y, 10, 0.42, size=17, color=col)
    y += 0.45

# branch / date
add_text(s, "branch: gui_improvements   ·   2026-06-12",
         0.45, 6.9, 10, 0.45, size=11, color=DIM, italic=True)


# ═══════════════════════════════════════════════════════════════════════════════
# SLIDE 2 — Platform Modernisation
# ═══════════════════════════════════════════════════════════════════════════════
s = prs.slides.add_slide(blank_layout)
set_bg(s)
add_rect(s, 0, 0, 0.08, 7.5, fill=ACCENT)
section_tag(s, "PLATFORM", ACCENT)

add_text(s, "Platform Modernisation",
         0.3, 0.55, 10, 0.75, size=34, bold=True, color=HEADING)
add_rect(s, 0.3, 1.35, 12.7, 0.04, fill=DIM)

# three columns
cols = [
    {
        "title": "Python 3.13  +  PyQt6",
        "color": ACCENT,
        "items": [
            "Removed deprecated APIs: imp, getargspec, QDesktopWidget",
            "PyQt5 → PyQt6 full migration across all UI code",
            "matplotlib backends: backend_qtagg fallback for PyQt6",
            "NumPy 2.x API fixes in C extension layer (PyFI.h)",
            "Access to Python 3.13 performance & free-thread mode",
        ],
    },
    {
        "title": "Windows Support",
        "color": GREEN,
        "items": [
            "Native launchers: gpi.cmd, gpi_init.cmd",
            "win_setup.py for one-step environment bootstrap",
            "conda environment.yml for reproducible install",
            "Spawn-based ProcessPoolExecutor (fork unsafe after Qt init)",
            "No WSL, no patching — works out of the box",
        ],
    },
    {
        "title": "Dark Theme  +  UI Polish",
        "color": YELLOW,
        "items": [
            "Full dark Fusion palette (theme.py)",
            "Correct Win32 title-bar colouring",
            "Settings dialog with live theme switching",
            "Compact node panels, visible toggle-button checked state",
            "New Library browser dialog replaces text-field path entry",
        ],
    },
]

col_w = 3.9
col_x = [0.3, 4.35, 8.4]
for i, col in enumerate(cols):
    x = col_x[i]
    add_rect(s, x, 1.5, col_w, 0.42, fill=col["color"])
    add_text(s, col["title"], x + 0.12, 1.52, col_w - 0.2, 0.38,
             size=13, bold=True, color=BG)
    bullet_block(s, col["items"], x, 2.02, col_w, 4.8,
                 size=13, dot_color=col["color"])


# ═══════════════════════════════════════════════════════════════════════════════
# SLIDE 3 — Voxel C++ Array Library
# ═══════════════════════════════════════════════════════════════════════════════
s = prs.slides.add_slide(blank_layout)
set_bg(s)
add_rect(s, 0, 0, 0.08, 7.5, fill=PEACH)
section_tag(s, "VOXEL  C++", PEACH)

add_text(s, "Voxel — C++ Array Library  (pybind11)",
         0.3, 0.55, 12, 0.75, size=34, bold=True, color=HEADING)
add_rect(s, 0.3, 1.35, 12.7, 0.04, fill=DIM)

# left column — what it is
add_text(s, "What it is", 0.3, 1.5, 5.8, 0.38,
         size=14, bold=True, color=PEACH)
bullet_block(s, [
    "Header-only C++ N-D array engine (Array<T>, 1–10D)",
    "PocketFFT backend — BSD-licensed, header-only, Apple Silicon safe",
    "Eigen linear algebra: GEMM, SVD, PCA, Cholesky, QR, Hermitian",
    "Discrete wavelet transform (1D–3D)",
    "pybind11 Python bridge — zero-copy: NumPy ↔ C++ share one buffer",
    "Replaces fragile cffi build system with make_pybind11.py (LRU cache)",
], 0.3, 1.95, 5.9, 4.6, size=13, dot_color=PEACH)

# right column — key optimisations
add_text(s, "Key optimisations", 6.5, 1.5, 6.5, 0.38,
         size=14, bold=True, color=PEACH)
bullet_block(s, [
    ("▶", "Fused FFT centering — parity mask during transform eliminates 2 full memory passes vs standard fftshift→FFT→fftshift"),
    ("▶", "64-byte aligned allocation — AVX-512 / NEON aligned loads on every array (generic libs default to 16/32-byte)"),
    ("▶", "Zero-copy bridge — slice / reshape / transpose return views; std::shared_ptr shared with Python"),
    ("▶", "In-place LinAlg API — pre-allocated output buffers eliminate heap allocation in iterative solver inner loops"),
    ("▶", "OpenMP SIMD pragmas in all kernels; explicit #pragma omp parallel for for user multicore loops"),
], 6.5, 1.95, 6.5, 4.2, size=13, dot_color=PEACH)

# footer stats
add_rect(s, 0.3, 6.6, 12.7, 0.04, fill=DIM)
add_text(s,
         "5,277-line HTML reference  ·  7 markdown guides  ·  296 unit tests  ·  benchmark suite",
         0.3, 6.68, 12.7, 0.45, size=11, color=DIM, italic=True)


# ═══════════════════════════════════════════════════════════════════════════════
# SLIDE 4 — Execution Engine  +  Memory
# ═══════════════════════════════════════════════════════════════════════════════
s = prs.slides.add_slide(blank_layout)
set_bg(s)
add_rect(s, 0, 0, 0.08, 7.5, fill=GREEN)
section_tag(s, "EXECUTION", GREEN)

add_text(s, "Execution Engine  +  Memory Architecture",
         0.3, 0.55, 12, 0.75, size=32, bold=True, color=HEADING)
add_rect(s, 0.3, 1.35, 12.7, 0.04, fill=DIM)

# --- left: execution
add_text(s, "GPI_PROCESS  —  Redesigned", 0.3, 1.5, 6.0, 0.38,
         size=14, bold=True, color=GREEN)
bullet_block(s, [
    "spawn-based ProcessPoolExecutor replaces unsafe fork — GPI_PROCESS works on Windows",
    "Pre-warmed worker pool: no 1–2 s cold-start tax on first heavy node",
    "GPI_NUM_WORKERS env var: full CPU saturation or serial debug mode",
    "QThreadPool for GPI_THREAD: reuses threads, fixes QThread-destroy crash",
    "Blocking watcher thread for GPI_PROCESS: zero-poll wait (was 100 wakeups/s per node)",
    "60 fps repaint throttling: 20 sequential nodes → 1 scene redraw",
], 0.3, 1.95, 6.0, 4.8, size=13, dot_color=GREEN)

# --- right: memory
add_text(s, "Memory Architecture", 6.6, 1.5, 6.3, 0.38,
         size=14, bold=True, color=GREEN)
bullet_block(s, [
    "Memmap port transfer: _PortDataRef descriptors replace pickling — 3 GB array uses ~100 bytes of queue bandwidth",
    "FileDescriptorManager (LRU eviction): eliminates 'too many open files' crash in deep pipelines",
    "ReadNPY zero-copy: mmap_mode='r' — peak RAM drops from 2× array size to near zero",
    "Reduce zero-copy slicing: slice(idx, idx+1) returns NumPy view, no per-compute allocation",
    "Status bar shows process RSS (matches Task Manager) — was showing misleading mapped-size >100%",
    "Parallel scheduler: startNextAvailableNode() runs independent branches concurrently",
], 6.6, 1.95, 6.3, 4.8, size=13, dot_color=GREEN)


# ═══════════════════════════════════════════════════════════════════════════════
# SLIDE 5 — ImageDisplay  +  Broken-Node Stubs
# ═══════════════════════════════════════════════════════════════════════════════
s = prs.slides.add_slide(blank_layout)
set_bg(s)
add_rect(s, 0, 0, 0.08, 7.5, fill=YELLOW)
section_tag(s, "UI / NODES", YELLOW)

add_text(s, "ImageDisplay Overhaul  +  Broken-Node Stubs",
         0.3, 0.55, 12, 0.75, size=30, bold=True, color=HEADING)
add_rect(s, 0.3, 1.35, 12.7, 0.04, fill=DIM)

# ImageDisplay
add_text(s, "ImageDisplay — Performance & Correctness", 0.3, 1.5, 6.2, 0.38,
         size=14, bold=True, color=YELLOW)
bullet_block(s, [
    ("✗→✓", "Channel-swap bug fixed: Format_RGB32 is [B,G,R,0xFF] — complex colormaps had R/B swapped since original authorship"),
    ("⚡", "No upfront data.copy(): only the displayed slice is allocated (up to N× memory saving)"),
    ("⚡", "np.clip replaces dual-mask ops — 2 full array allocations eliminated per compute"),
    ("⚡", "GPI_THREAD exec type — compute no longer blocks the UI event loop"),
    ("🎯", "Multi-ROI: unlimited mixed types (pointer, line, rect, ellipse, polygon) with unique palette colors"),
    ("🎯", "Catmull-Rom smooth polygon ROI — drawn mask matches displayed curve exactly"),
    ("🎯", "3D propagation: replicate 2D ROI mask across full volume"),
    ("🎯", "Mask input/output ports: labeled uint8 arrays for downstream nodes"),
], 0.3, 1.95, 6.2, 5.0, size=12, dot_color=YELLOW)

# Broken-node stubs
add_text(s, "Broken-Node Stub System", 6.7, 1.5, 6.0, 0.38,
         size=14, bold=True, color=RED)
bullet_block(s, [
    "GPI 1.4.5: import error → node silently dropped, all connections lost",
    "_BrokenNodeCatalogItem stub preserves all port connections (typed PASS)",
    "Visual: red dashed border + X-cross drawn below title (title remains readable)",
    "Fix-reload-continue: fixing the file and reloading restores full functionality, original widget settings, and upstream recompute",
    "",
    "PyTorch GPU Port Type",
    "TORCH_TENSOR as first-class GPI port type",
    "Serialises GPU tensors via memmap for inter-process transfer",
    "Type validation checks dtype + device at wire time — catches mismatches before compute()",
], 6.7, 1.95, 6.0, 5.0, size=12, dot_color=RED)


# ═══════════════════════════════════════════════════════════════════════════════
# SLIDE 6 — Node-Level Bug Fixes  (summary)
# ═══════════════════════════════════════════════════════════════════════════════
s = prs.slides.add_slide(blank_layout)
set_bg(s)
add_rect(s, 0, 0, 0.08, 7.5, fill=RED)
section_tag(s, "NODE FIXES", RED)

add_text(s, "Node-Level Bug Fixes  &  Performance",
         0.3, 0.55, 12, 0.75, size=34, bold=True, color=HEADING)
add_rect(s, 0.3, 1.35, 12.7, 0.04, fill=DIM)

rows = [
    #  node               category    what changed
    ("ValueBounds",       "CRASH",    "scipy.stats.threshold removed in scipy 1.0 — replaced with np.where",                          RED),
    ("Calc101",           "CRASH",    "cumtrapz removed in scipy 1.11; 'import integrate as int' shadowed Python int",                 RED),
    ("Float_Math",        "BUG",      "bare except swallowed all errors; dead widget ref; if/elif chain fixed",                        YELLOW),
    ("CrossSection",      "COMPAT",   "hardcoded backend_qt5agg → crashes PyQt6; fixed with backend_qtagg fallback",                  ACCENT),
    ("Matplotlib (×2)",   "COMPAT",   "same backend_qt5agg crash in Matplotlib_GPI and Matplotlib_sim_GPI; SubplotToolQt wrapped",    ACCENT),
    ("FFT_NUMPY",         "PERF",     "np.insert/delete zero-padding replaced with np.pad — 10–50× faster for large arrays",          GREEN),
    ("Zeropad (sinc)",    "PERF",     "same np.pad fix + N per-dim IFFTs collapsed to 1 batched IFFT: N+1 → 2 FFT calls",            GREEN),
    ("Combine / Glue",    "PERF",     "np.append replaced with np.concatenate — eliminates hidden array flatten/copy",                 GREEN),
    ("Reshape",           "BUG",      "data.shape = out_dims mutated upstream port array in-place → data.reshape()",                  YELLOW),
    ("Dimensions",        "BUG",      "out = data; out.shape = ... mutated upstream array in Reshape/Combine/Split/Extend/Tile modes", YELLOW),
    ("Collapse",          "CLEANUP",  "print() debug statement and unused import scipy in production code removed",                    DIM),
    ("Statistics",        "ENHANCE",  "Added sum + median output ports; complex support (|data|); dtype + element count display",      PEACH),
    ("Interpolate",       "COMPAT",   "scipy.ndimage.interpolation.map_coordinates → scipy.ndimage.map_coordinates",                  ACCENT),
    ("SheppLogan",        "ENHANCE",  "Added 3D option: (Slices×n×n) float32 volume, broadcast xy+z to avoid full coord grid alloc",  PEACH),
]

# table header
hx = [0.3, 2.15, 3.45, 11.2]
add_rect(s, 0.3, 1.45, 12.7, 0.32, fill=RGBColor(0x31, 0x32, 0x4a))
for txt, x in zip(["Node", "Type", "Change"], hx):
    add_text(s, txt, x, 1.47, 2.0, 0.28, size=11, bold=True, color=HEADING)

row_h = 0.325
y = 1.77
for i, (node, cat, change, col) in enumerate(rows):
    bg = RGBColor(0x28, 0x28, 0x3a) if i % 2 == 0 else RGBColor(0x1e, 0x1e, 0x2e)
    add_rect(s, 0.3, y, 12.7, row_h, fill=bg)
    # node name
    add_text(s, node,   0.35, y + 0.03, 1.75, row_h - 0.04, size=11, bold=True,  color=HEADING)
    # category pill
    add_rect(s, 2.15, y + 0.05, 1.2, row_h - 0.12, fill=col)
    add_text(s, cat,    2.2,  y + 0.06, 1.1,  row_h - 0.14, size=9,  bold=True,  color=BG)
    # description
    add_text(s, change, 3.5,  y + 0.03, 9.4,  row_h - 0.04, size=10, bold=False, color=BODY)
    y += row_h


# ── save ──────────────────────────────────────────────────────────────────────
out_path = r"c:\Users\310217414\Documents\SW\gpi_source\GPI_2.0_Changes.pptx"
prs.save(out_path)
print(f"Saved: {out_path}")
