## Full Feature List — Priority Order

---

### 🔴 Round 1 — High Impact, Already Have the Tools (PyMuPDF)

1. Password protect PDF
2. Unlock / decrypt PDF
3. Rotate PDF pages
4. Watermark PDF (text or image)
5. Add page numbers to PDF
6. Compression level selector (low / medium / high) with estimated size preview
7. DPI selector for PDF to Images (72 / 150 / 300)
8. Image format selector for PDF to Images (PNG / JPEG / WEBP)
9. Quality slider for PNG to JPG (currently hardcoded 95)
10. Reorder PDF pages (drag and drop before merge)
11. Better merge UI — show file order, drag to reorder

---

### 🔴 Round 2 — High Demand Tool Gaps (competitors all have these)

12. PDF to Excel
13. Excel to PDF
14. PowerPoint to PDF
15. PDF to PowerPoint
16. HTML to PDF
17. OCR — scanned PDF to searchable PDF (Tesseract already in project)
18. Extract text from PDF → .txt file
19. Extract images from PDF → .zip of all embedded images

---

### 🔴 Round 3 — Upload & Processing UX (users expect this)

20. Batch processing — convert multiple files at once, see all statuses together
21. Multi-file status page — one page showing all batch jobs live
22. ZIP download for batch results
23. URL upload — paste a URL, DocShift fetches and converts
24. Real progress percentage — page-by-page via PyMuPDF, not just shimmer bar

---

### 🟡 Round 4 — Download & Sharing

25. Copy download link — one-click copy with expiry warning shown
26. Email download link — send result link to email
27. QR code for download — scan on mobile
28. Re-download expired file notice — instead of silent 404, show "expired, reconvert"

---

### 🟡 Round 5 — Dashboard Completeness

29. Dashboard pagination — currently loads all jobs into one page
30. Job retry from dashboard — one-click retry failed jobs with same file
31. Storage usage indicator — show how much space user's files take
32. Conversion history export — download CSV of all job history
33. Usage stats on account page — charts of conversions over time, most used tools

---

### 🟡 Round 6 — Tool Enhancements (polish existing tools)

34. PDF metadata editor — edit title, author, subject, keywords
35. Flatten PDF — flatten form fields and annotations
36. Grayscale PDF — convert colour PDF to black and white
37. Crop PDF pages — define crop box
38. Compare two PDFs — highlight differences

---

### 🟢 Round 7 — Homepage & UX Polish

39. Tool search on homepage — live filter the tool grid
40. Recently used tools — show last 3 used tools at top
41. Tool category colour accents — PDF=red, Office=blue, Image=amber (already partially there)
42. Conversion tips per tool — contextual pro tips below upload zone
43. Keyboard shortcuts — power user feature

---

### 🟢 Round 8 — Developer / Power User Features

44. API access for authenticated users — generate API key, POST files programmatically
45. Webhook on job completion — POST to user's URL when done
46. SDK code snippets — show curl / Python / JS example after conversion

---

### 🟢 Round 9 — Legal & Trust (needed before going public)

47. Terms of Service page
48. Privacy Policy page
49. Custom 404 page
50. Custom 500 page
51. Cookie consent banner (required in EU/India)

---

## Summary Table

| Round | Priority | Count | Effort |
|---|---|---|---|
| 1 | 🔴 PyMuPDF tools | 11 | Low–Medium |
| 2 | 🔴 New tool gaps | 8 | Medium–High |
| 3 | 🔴 Upload/processing UX | 5 | Medium |
| 4 | 🟡 Download & sharing | 4 | Low |
| 5 | 🟡 Dashboard | 5 | Low–Medium |
| 6 | 🟡 Tool polish | 5 | Medium |
| 7 | 🟢 UX polish | 5 | Low |
| 8 | 🟢 Developer features | 3 | High |
| 9 | 🟢 Legal/trust | 5 | Low |

---

Tell me which numbers you want to pick up and I'll start building.