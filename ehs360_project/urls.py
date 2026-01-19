"""
URL configuration for ehs360_project project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('apps.accounts.urls')),
    path('dashboards/', include('apps.dashboards.urls')),
    path('organizations/', include('apps.organizations.urls')), 
    path('accidents/', include('apps.accidents.urls')),  
    path('hazards/', include('apps.hazards.urls')),  
    path('inspections/', include('apps.inspections.urls')),
    # path('data_collection/', include('apps.data_collection.urls')),
    path('env-data/', include('apps.ENVdata.urls')),
    path('notifications/', include('apps.notifications.urls')),


    #path('observations/', include('apps.observations.urls')),

    # Redirect root to login
    path('', RedirectView.as_view(url='/accounts/login/', permanent=False)),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)