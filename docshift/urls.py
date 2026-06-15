from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView
from django.http import JsonResponse, HttpResponse

def health_check(request):
    return JsonResponse({'status': 'ok'})

def robots_txt(request):
    lines = [
        "User-agent: *",
        "Disallow: /admin/",
        "Disallow: /auth/",
        "Disallow: /dashboard/",
        "Disallow: /job/",
        "Disallow: /editor/session/",
        "Disallow: /api/v1/",
        "Allow: /",
        "Sitemap: https://shiftdocs.io/sitemap.xml",
    ]
    return HttpResponse("\n".join(lines), content_type="text/plain")

def sitemap_xml(request):
    xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
<url>
<loc>https://shiftdocs.io/</loc>
<lastmod>2026-06-15</lastmod>
<changefreq>daily</changefreq>
<priority>1</priority>
</url>
<url>
<loc>https://shiftdocs.io/pricing/</loc>
<lastmod>2026-06-15</lastmod>
<changefreq>daily</changefreq>
<priority>0.9</priority>
</url>
<url>
<loc>https://shiftdocs.io/faq/</loc>
<lastmod>2026-06-15</lastmod>
<changefreq>daily</changefreq>
<priority>0.9</priority>
</url>
<url>
<loc>https://shiftdocs.io/digital-sign/</loc>
<lastmod>2026-06-15</lastmod>
<changefreq>daily</changefreq>
<priority>0.9</priority>
</url>
<url>
<loc>https://shiftdocs.io/editor/</loc>
<lastmod>2026-06-15</lastmod>
<changefreq>daily</changefreq>
<priority>0.9</priority>
</url>
<url>
<loc>https://shiftdocs.io/api/docs/</loc>
<lastmod>2026-06-15</lastmod>
<changefreq>daily</changefreq>
<priority>0.9</priority>
</url>
<url>
<loc>https://shiftdocs.io/terms/</loc>
<lastmod>2026-06-15</lastmod>
<changefreq>daily</changefreq>
<priority>0.9</priority>
</url>
<url>
<loc>https://shiftdocs.io/privacy/</loc>
<lastmod>2026-06-15</lastmod>
<changefreq>daily</changefreq>
<priority>0.9</priority>
</url>
<url>
<loc>https://shiftdocs.io/tool/compress_pdf/</loc>
<lastmod>2026-06-15</lastmod>
<changefreq>daily</changefreq>
<priority>0.9</priority>
</url>
<url>
<loc>https://shiftdocs.io/tool/merge_pdf/</loc>
<lastmod>2026-06-15</lastmod>
<changefreq>daily</changefreq>
<priority>0.9</priority>
</url>
<url>
<loc>https://shiftdocs.io/tool/split_pdf/</loc>
<lastmod>2026-06-15</lastmod>
<changefreq>daily</changefreq>
<priority>0.9</priority>
</url>
<url>
<loc>https://shiftdocs.io/tool/pdf_to_word/</loc>
<lastmod>2026-06-15</lastmod>
<changefreq>daily</changefreq>
<priority>0.9</priority>
</url>
<url>
<loc>https://shiftdocs.io/tool/pdf_to_excel/</loc>
<lastmod>2026-06-15</lastmod>
<changefreq>daily</changefreq>
<priority>0.9</priority>
</url>
<url>
<loc>https://shiftdocs.io/tool/pdf_to_pptx/</loc>
<lastmod>2026-06-15</lastmod>
<changefreq>daily</changefreq>
<priority>0.9</priority>
</url>
<url>
<loc>https://shiftdocs.io/tool/ocr_pdf/</loc>
<lastmod>2026-06-15</lastmod>
<changefreq>daily</changefreq>
<priority>0.9</priority>
</url>
<url>
<loc>https://shiftdocs.io/tool/pdf_to_images/</loc>
<lastmod>2026-06-15</lastmod>
<changefreq>daily</changefreq>
<priority>0.9</priority>
</url>
<url>
<loc>https://shiftdocs.io/tool/password_protect/</loc>
<lastmod>2026-06-15</lastmod>
<changefreq>daily</changefreq>
<priority>0.9</priority>
</url>
<url>
<loc>https://shiftdocs.io/tool/unlock_pdf/</loc>
<lastmod>2026-06-15</lastmod>
<changefreq>daily</changefreq>
<priority>0.9</priority>
</url>
<url>
<loc>https://shiftdocs.io/tool/rotate_pdf/</loc>
<lastmod>2026-06-15</lastmod>
<changefreq>daily</changefreq>
<priority>0.9</priority>
</url>
<url>
<loc>https://shiftdocs.io/tool/watermark_pdf/</loc>
<lastmod>2026-06-15</lastmod>
<changefreq>daily</changefreq>
<priority>0.9</priority>
</url>
<url>
<loc>https://shiftdocs.io/tool/add_page_numbers/</loc>
<lastmod>2026-06-15</lastmod>
<changefreq>daily</changefreq>
<priority>0.9</priority>
</url>
<url>
<loc>https://shiftdocs.io/tool/edit_metadata/</loc>
<lastmod>2026-06-15</lastmod>
<changefreq>daily</changefreq>
<priority>0.9</priority>
</url>
<url>
<loc>https://shiftdocs.io/tool/flatten_pdf/</loc>
<lastmod>2026-06-15</lastmod>
<changefreq>daily</changefreq>
<priority>0.9</priority>
</url>
<url>
<loc>https://shiftdocs.io/tool/grayscale_pdf/</loc>
<lastmod>2026-06-15</lastmod>
<changefreq>daily</changefreq>
<priority>0.9</priority>
</url>
<url>
<loc>https://shiftdocs.io/tool/crop_pdf/</loc>
<lastmod>2026-06-15</lastmod>
<changefreq>daily</changefreq>
<priority>0.9</priority>
</url>
<url>
<loc>https://shiftdocs.io/tool/extract_text/</loc>
<lastmod>2026-06-15</lastmod>
<changefreq>daily</changefreq>
<priority>0.9</priority>
</url>
<url>
<loc>https://shiftdocs.io/tool/extract_images/</loc>
<lastmod>2026-06-15</lastmod>
<changefreq>daily</changefreq>
<priority>0.9</priority>
</url>
<url>
<loc>https://shiftdocs.io/tool/docx_to_pdf/</loc>
<lastmod>2026-06-15</lastmod>
<changefreq>daily</changefreq>
<priority>0.9</priority>
</url>
<url>
<loc>https://shiftdocs.io/tool/excel_to_pdf/</loc>
<lastmod>2026-06-15</lastmod>
<changefreq>daily</changefreq>
<priority>0.9</priority>
</url>
<url>
<loc>https://shiftdocs.io/tool/pptx_to_pdf/</loc>
<lastmod>2026-06-15</lastmod>
<changefreq>daily</changefreq>
<priority>0.9</priority>
</url>
<url>
<loc>https://shiftdocs.io/tool/txt_to_pdf/</loc>
<lastmod>2026-06-15</lastmod>
<changefreq>daily</changefreq>
<priority>0.9</priority>
</url>
<url>
<loc>https://shiftdocs.io/tool/html_to_pdf/</loc>
<lastmod>2026-06-15</lastmod>
<changefreq>daily</changefreq>
<priority>0.9</priority>
</url>
<url>
<loc>https://shiftdocs.io/tool/img_to_pdf/</loc>
<lastmod>2026-06-15</lastmod>
<changefreq>daily</changefreq>
<priority>0.9</priority>
</url>
<url>
<loc>https://shiftdocs.io/tool/jpg_to_png/</loc>
<lastmod>2026-06-15</lastmod>
<changefreq>daily</changefreq>
<priority>0.9</priority>
</url>
<url>
<loc>https://shiftdocs.io/tool/png_to_jpg/</loc>
<lastmod>2026-06-15</lastmod>
<changefreq>daily</changefreq>
<priority>0.9</priority>
</url>
<url>
<loc>https://shiftdocs.io/tool/resize_image/</loc>
<lastmod>2026-06-15</lastmod>
<changefreq>daily</changefreq>
<priority>0.9</priority>
</url>
</urlset>
"""
    return HttpResponse(xml_content, content_type="application/xml")

urlpatterns = [
    path('robots.txt', robots_txt, name='robots_txt'),
    path('sitemap.xml', sitemap_xml, name='sitemap_xml'),
    path('health/', health_check, name='health_check'),

    path('admin/', admin.site.urls),
    path('auth/', include('allauth.urls')),
    path('', include('converter.urls')),
    path('api/', include('api.urls')),
    path('editor/', include('editor.urls')),

    # Retired features — redirect to homepage
    path('translator/', RedirectView.as_view(url='/', permanent=False)),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
