from django.urls import path
from . import views

urlpatterns = [
    path('',                            views.translator_home,        name='translator_home'),
    path('upload/',                     views.translator_upload,      name='translator_upload'),
    path('job/<uuid:job_id>/',          views.translator_result,      name='translator_result'),
    path('job/<uuid:job_id>/status/',   views.translator_status_json, name='translator_status_json'),
    path('job/<uuid:job_id>/download/', views.translator_download,    name='translator_download'),
]
