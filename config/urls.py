from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path('admin/', admin.site.urls),
    path('manage/', include('hr.urls')),
    path('', include('leave.urls')),
]

# Serve uploaded files through Django so attachments work under gunicorn too.
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)