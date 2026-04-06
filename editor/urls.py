from django.urls import path
from . import views

urlpatterns = [
    path('',                                                      views.editor_home,        name='editor_home'),
    path('upload/',                                               views.editor_upload,      name='editor_upload'),
    path('session/<uuid:session_id>/',                            views.editor_session,     name='editor_session'),
    path('session/<uuid:session_id>/status/',                     views.editor_status_json, name='editor_status_json'),
    path('session/<uuid:session_id>/save/',                       views.editor_save,        name='editor_save'),
    path('session/<uuid:session_id>/download/',                   views.editor_download,    name='editor_download'),
    path('session/<uuid:session_id>/page/<int:page_number>/',     views.editor_page_image,  name='editor_page_image'),
]
