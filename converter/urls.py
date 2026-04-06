from django.urls import path
from . import views

urlpatterns = [
    path('',                                        views.index,                name='index'),
    path('dashboard/',                              views.dashboard,             name='dashboard'),
    path('dashboard/api/',                          views.dashboard_api,         name='dashboard_api'),
    path('dashboard/clear/',                        views.dashboard_clear,       name='dashboard_clear'),
    path('dashboard/delete/<uuid:uuid>/',           views.dashboard_delete_job,  name='dashboard_delete_job'),
    path('convert/',                                views.universal_upload,      name='universal_upload'),

    # ── Rotate PDF — specific routes BEFORE the generic tool routes ──
    path('tool/rotate_pdf/preview/<uuid:job_id>/',  views.rotate_preview,        name='rotate_preview'),
    path('tool/rotate_pdf/apply/<uuid:job_id>/',    views.rotate_apply,          name='rotate_apply'),

    # ── Generic tool routes ───────────────────────────────────────────
    path('tool/<str:tool_slug>/',                   views.upload_form,           name='upload_form'),
    path('tool/<str:tool_slug>/upload/',            views.upload_file,           name='upload_file'),

    path('job/<uuid:uuid>/status/',                 views.job_status,            name='job_status'),
    path('job/<uuid:uuid>/status/json/',            views.job_status_json,       name='job_status_json'),
    path('job/<uuid:uuid>/preview/',                views.job_preview,           name='job_preview'),
    path('job/<uuid:uuid>/download/',               views.job_download,          name='job_download'),
    path('account/',                                views.account,               name='account'),
    
    # ── Static Info Pages ────────────────────────────────────────────
    path('terms/',                                  views.terms_view,            name='terms'),
    path('pricing/',                                views.pricing_view,          name='pricing'),
    path('contact-sales/',                          views.contact_sales,         name='contact_sales'),
    path('privacy/',                                views.privacy_view,          name='privacy'),

    path('job/<uuid:uuid>/retry/',                  views.job_retry,             name='job_retry'),
    path('dashboard/export/csv/',                   views.export_csv,            name='export_csv'),

    path('batch/<str:batch_id>/',              views.batch_status,       name='batch_status'),
    path('batch/<str:batch_id>/status/json/',  views.batch_status_json,  name='batch_status_json'),
    path('batch/<str:batch_id>/download-zip/', views.batch_download_zip, name='batch_download_zip'),

    path('convert/url/', views.url_upload, name='url_upload'),
]