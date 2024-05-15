from django.contrib import admin
from django.urls import path
from CEMAConnector.views import SubespView, UnidView, EspecialidadeBasica, ConvenioDetalhesView, PlanosDisponiveis, BuscarConvenioView, BuscarPacienteView, CadastrarNovoPaciente, BuscarDataDisponivel, BuscarHorario, RealizarAgendamento

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/subesp/', SubespView.as_view(), name='subesp-api'),
    path('api/unid/', UnidView.as_view(), name='unid-api'),
    path('api/especialidade_basica/', EspecialidadeBasica.as_view(), name='especialidade-basica-api'),
    path('api/planos_disponiveis/', PlanosDisponiveis.as_view(), name='planos-disponiveis-api'),
    path('api/convenios_disponiveis/', ConvenioDetalhesView.as_view(), name='convenios_disponiveis'),
    path('api/buscar-paciente/', BuscarPacienteView.as_view(), name='buscar-paciente'),
    path('api/buscar-convenio/', BuscarConvenioView.as_view(), name='buscar-convenio'),
    path('api/cadastrar-paciente/', CadastrarNovoPaciente.as_view(), name='cadastrar-paciente'),
    path('api/buscardata/', BuscarDataDisponivel.as_view(), name='buscar-data-disponivel'),
    path('api/buscarhorario/', BuscarHorario.as_view(), name='buscar-horario-disponivel'),
    path('api/registrar-agendamento/', RealizarAgendamento.as_view(), name='realizar-agendamento'),

]
