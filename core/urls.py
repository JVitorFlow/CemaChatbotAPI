from django.contrib import admin
from django.urls import path
from CEMAConnector.views import SubespView, UnidView, ProcedView, ConvPlanView, BuscarConvenioView, BuscarPacienteView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/subesp/', SubespView.as_view(), name='subesp-api'),
    path('api/unid/', UnidView.as_view(), name='unid-api'),
    path('api/proced/', ProcedView.as_view(), name='proced-api'),
    path('api/conv_plan/', ConvPlanView.as_view(), name='conv_plan-api'),
    
    path('api/buscar-paciente/', BuscarPacienteView.as_view(), name='buscar-paciente'),
    path('api/buscar-convenio/', BuscarConvenioView.as_view(), name='buscar-convenio'),
]
