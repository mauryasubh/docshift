# PDF Editor — Stage 2: Page Management & UI Polish

Stage 1 established the "Content Editor" (editing text/images within a page). Stage 2 transforms DocShift into a "Document Manager" by allowing users to manipulate the structure of the PDF itself and providing a more premium, fluid interface.

## 🛠️ Planned Features

### 1. Page Operations (Sidebar)
Users need to manage the document at a high level.
- **Thumbnails Sidebar**: Visual list of all pages in the PDF.
- **Drag & Drop**: Native JS/SortableJS to reorder pages.
- **Delete Pages**: Quick trash icon to remove unnecessary pages.

### 2. UI/UX Polishing
Moving away from "Minimum Viable" to "Premium Tool."
- **Custom Text Modals**: Replace `prompt()` with an inline, styled text editor.
- **Zoom Controls**: In/Out/Fit controls in the toolbar.
- **Panel Improvements**: Sleek, accordion-style groups in the right panel.

### 3. Global Search & Redact
A powerful utility for document preparation.
- **Search Panel**: Find all occurrences of a string.
- **Bulk Redact**: Black out all search results with one click.

## ⚙️ Backend Changes
- **`save_edits_task`**: Update to handle `page_map` for reordering and deletion using `PyMuPDF`.
- **OCR Quality**: Optionally support 300 DPI for cleaner results on scanned docs.
