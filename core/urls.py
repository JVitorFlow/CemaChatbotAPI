from django.contrib import admin
from django.urls import path
from CEMAConnector.views import SubespView, UnidView, EspecialidadeBasica, ConvenioDetalhesView, BuscarConvenioView, BuscarPacienteView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/subesp/', SubespView.as_view(), name='subesp-api'),
    path('api/unid/', UnidView.as_view(), name='unid-api'),
    path('api/especialidade_basica/', EspecialidadeBasica.as_view(), name='especialidade-basica-api'),
    path('api/convenios_disponiveis/', ConvenioDetalhesView.as_view(), name='convenios_disponiveis'),
    
    path('api/buscar-paciente/', BuscarPacienteView.as_view(), name='buscar-paciente'),
    path('api/buscar-convenio/', BuscarConvenioView.as_view(), name='buscar-convenio'),
]
