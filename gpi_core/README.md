# Core Nodes

## Reading PRIDE XML/REC images

Add **fileIO > ReadREC**, browse to either the `.xml` or `.rec` file, and enable
**Read**. Both files must have the same base name and be in the same folder.
Connect **out** directly to **ImageDisplay** to browse the slices.
Alternatively, drop a `.rec` file onto the GPI canvas to create **ReadREC** with
the file selected, then enable **Read**. The `.rec` association is case-insensitive.

The reader supports PRIDE_V5 XML with signed or unsigned 8-bit/16-bit REC pixels.
It outputs a `float32` array shaped `(image, row, column)`. Images are grouped by
acquisition keys (label, gradient, b-value, dynamic, phase, echo, type, sequence)
and sorted by slice number within each group. REC offsets use the XML `Index`,
so wrapped/interleaved storage does not scramble slice order.
Intensity values match RecViewer's displayed values:
`stored_pixel * Rescale Slope + Rescale Intercept`, not Philips floating-point
scaling. No anatomical reorientation is performed.
