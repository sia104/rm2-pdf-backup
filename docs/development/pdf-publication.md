# PDF publication behaviour

`run-local` renders documents into staging first. A staged PDF is only copied into the visible PDF mirror after validation succeeds.

Publication rules:

- failed renders are recorded in the manifest and are not published;
- invalid staged PDFs are not published;
- valid staged PDFs are copied into `pdf_current` using the planned visible relative path;
- publication uses a temporary destination file and atomic replace;
- a failed document does not replace a previous good PDF.

This keeps the raw backup as the recovery source of truth while allowing the visible PDF mirror to contain only validated outputs.
