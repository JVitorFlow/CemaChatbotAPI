from django.contrib import admin
from django.urls import path
from CEMAConnector.views import DynamicDataQuery

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/DynamicDataQuery', DynamicDataQuery.as_view(), name='DynamicDataQuery'),
]
