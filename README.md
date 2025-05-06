# pdf (WIP)

Tools to read and edit PDFs based on the PyMuPDF (fitz) library.

This supports the following optional environment variable:

- `ALLOWED_DIR`: The allowed directory. If supplied, the tools will only be able to read/write within this directory. To allow multiple directories, supply a strictly valid JSON-encoded list e.g. use double quotes: '["dir_a", "dir_b"]'

