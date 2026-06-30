# Template render probe

This diagnostic checks whether copied RM2 documents with detectable template references produce rendered SVG output that appears to contain template/background drawing primitives.

It is intentionally conservative:

- it does not upload rendered PDFs;
- it does not upload page images;
- it records copied template counts and hashes;
- it records detected document template references;
- it records SVG size and primitive counts for a few pages per referenced document.

A definitive exactness test still requires a known test page that uses a visually obvious template or custom DIAD form. If the probe shows no background-like SVG content, the next step is to implement an explicit template-background composition layer.
