from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import JSONParser
from decouple import config
from .utils.ssh_utils import get_ssh_client
import re
import paramiko
from datetime import datetime
from django.http import JsonResponse
import logging
import os
from django.conf import settings
from .utils.mappings import get_unidade_by_nome, get_unidade_by_codigo


logger = logging.getLogger('django')


def load_sql_file(filename):
    try:
        filepath = os.path.join(settings.BASE_DIR, 'CEMAConnector', 'sql', filename)
        with open(filepath, 'r', encoding='utf-8') as file:
            return file.read()
    except Exception as e:
        print(f"Erro ao carregar o arquivo SQL: {e}")
        return None


class BaseView(APIView):
    parser_classes = [JSONParser]

    @staticmethod
    def process_output(output, column_names):
        if not column_names:
            logger.info("Aviso: 'column_names' está None, nenhum dado será processado.")
            return []

        data = []
        lines = output.split('\n')
        data_line_regex = re.compile(r'^\s*\d+')  # Regex para identificar linhas que começam com dígitos

        for line in lines:
            if data_line_regex.match(line):  # Assegura que a linha começa com dígitos
                parts = [part.strip() for part in line.split('|')]
                if len(parts) == len(column_names):
                    record = dict(zip(column_names, parts))
                    data.append(record)
                else:
                    logger.info(f"Erro de formatação: número incorreto de colunas em:  {line}")
            else:
                logger.info(f"Linha descartada por não corresponder ao formato esperado: {line}")
        return data

    
    def query_database(self, table_name=None, column_names=None, request=None, custom_query=None):

        if custom_query:
            plsql_block = custom_query
            logger.info(f"executando custom query {plsql_block}")
        else:    
            filters = request.data.get('filters', {})
            where_clause = " AND ".join([f"{column} = '{value}'" for column, value in filters.items() if column in column_names])

            plsql_block = load_sql_file('query.sql')
        
            # Substituir os placeholders no SQL com os valores reais
            plsql_block = plsql_block.format(
                columns=", ".join(column_names),
                table=table_name,
                where_clause=f'WHERE {where_clause}' if where_clause else ''
            )
        
        try:
            client = get_ssh_client(settings.HOSTNAME, settings.SSH_PORT, settings.USERNAME, settings.PASSWORD)
            stdin, stdout, stderr = client.exec_command(f"""
            export LD_LIBRARY_PATH={settings.SQLPLUS_PATH}:$LD_LIBRARY_PATH
            export PATH={settings.SQLPLUS_PATH}:$PATH
            echo "{plsql_block}" | sqlplus -S {settings.CONNECTION_STRING}
            """)
            
            errors = stderr.read().decode('utf-8')
            if errors:
                return Response({"error": errors}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            output = stdout.read().decode('utf-8').strip()
            # Decidindo sobre o processamento de saída
            if not custom_query:
                data = [
                    dict(zip(column_names, re.sub(r'\s+', ' ', line).strip().split('|')))
                    for line in output.split('\n') if line and not line.startswith('-') and not line.isspace()
                ]
            else:
                data = BaseView.process_output(output, column_names)

            return Response({"data": data}, status=status.HTTP_200_OK)
        except paramiko.SSHException as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class SubespView(BaseView):
    parser_classes = [JSONParser]

    def post(self, request, format=None):
        subespecialidade = request.data.get('subespecialidade', '').strip()

        if subespecialidade:
            where_clause = f"UPPER(VSUES_DS) LIKE '%{subespecialidade.upper()}%'"
            order_by = "ORDER BY VSUES_DS, VPRRE_DS"  # Agora também ordenando por especialidade

            # Verificar se a subespecialidade existe
            check_query = load_sql_file('subespecialidade.sql')
        
            # Substituir os placeholders no SQL com os valores reais
            check_query = check_query.format(where_clause=where_clause)

            check_response = self.query_database(custom_query=check_query, column_names=["COUNT"])
            if check_response.status_code != 200:
                return Response({"data": "Falha ao buscar dados", "details": check_response.data}, status=check_response.status_code)

            count_data = check_response.data.get('data', [])
            if not count_data or int(count_data[0]['COUNT']) == 0:
                return Response({"data": f"Subespecialidade '{subespecialidade}' não encontrada."}, status=status.HTTP_404_NOT_FOUND)

        else:
            # Lista de subespecialidades sugeridas
            sugestoes = [
                'GLAUCOMA', 'CATARATA', 'RETINA', 'ESTRABISMO', 'CORNEA CIRURGICO',
                'MIOPIA / REFRATIVA', 'VITRECTOMIA', 'PROTESE OCULAR', 'ALERGIA OCULAR',
                'BLEFARITE', 'OLHOS SECOS', 'PLASTICA OCULAR', 'CERATOCONE',
                'TRANSPLANTE CORNEA', 'LENTE DE CONTATO'
            ]
            subespecialidades_sugeridas = ', '.join(f"'{sub}'" for sub in sugestoes)
            where_clause = f"VSUES_DS IN ({subespecialidades_sugeridas})"
            order_by = "ORDER BY VPRRE_DS, VSUES_DS"  # Priorizar ordenação por especialidade quando sugestões forem usadas

        subesp_query = load_sql_file('ConsultaSubespLimitada.sql')
        # Substituir os placeholders no SQL com os valores reais
        subesp_query = subesp_query.format(where_clause=where_clause, order_by=order_by)
        response = self.query_database(custom_query=subesp_query, column_names=["VSUES_CD", "VSUES_DS", "VPRRE_DS"])
        if response.status_code != 200:
            return Response({"error": "Falha ao buscar dados", "details": response.data}, status=response.status_code)

        subespecialidades = response.data.get('data', [])

        return Response({"data": subespecialidades}, status=status.HTTP_200_OK)


class UnidView(BaseView):
    parser_classes = [JSONParser]

    column_names = ['VUNID_CD', 'VUNID_DS', 'VLOGRADOURO', 'VNR', 'VCOMPL', 'VBAIRRO', 'VCIDADE', 'VCEP', 'VUF', 'VDDD', 'VTEL', 'VRAMAL', 'VUNID_APRES', 'VUNID_LOCAL']
    table_name = 'V_APP_UNID'

    def post(self, request, format=None):
        unidade = request.data.get('unidade', '').strip()

        if unidade:
            where_clause = f"UPPER(VUNID_DS) LIKE '%{unidade.upper()}%'"
            order_by = "ORDER BY VUNID_DS"

            # Verificar se a unidade existe
            check_query = load_sql_file('verifica_unidade.sql')
        
            # Substituir os placeholders no SQL com os valores reais
            check_query = check_query.format(table_name=self.table_name, where_clause=where_clause)
            check_response = self.query_database(custom_query=check_query, column_names=["COUNT"])
            if check_response.status_code != 200:
                return Response({"error": "Falha ao buscar dados", "details": check_response.data}, status=check_response.status_code)

            count_data = check_response.data.get('data', [])
            if not count_data or int(count_data[0]['COUNT']) == 0:
                return Response({"data": f"Unidade '{unidade}' não encontrada."}, status=status.HTTP_404_NOT_FOUND)
        else:
            # Sem filtro de unidade, trazer todas
            where_clause = "1=1"  # Isso é usado para garantir que a consulta funcione sem filtro específico
            order_by = "ORDER BY VUNID_DS"
            

        unid_query = load_sql_file('unidade.sql')        
        # Substituir os placeholders no SQL com os valores reais
        unid_query = unid_query.format(table_name=self.table_name, where_clause=where_clause, order_by=order_by)

        logger.info(f"Executando consulta {unid_query}")
        unid_response = self.query_database(custom_query=unid_query, column_names=self.column_names)
        if unid_response.status_code != 200:
            return unid_response

        unidades = unid_response.data.get('data', [])
        return Response({"data": unidades}, status=status.HTTP_200_OK)
class EspecialidadeBasica(BaseView):
    parser_classes = [JSONParser]
    column_names = ['vGPRO_CD', 'VGPRO_DS','VPRRE_CD','VPRRE_DS','VITCO_CD']
    table_name = 'V_APP_PROCED'

    def post(self, request, format=None):
        return self.query_database(self.table_name, self.column_names, request)

# Pesquisar Planos disponiveis    
class PlanosDisponiveis(BaseView):
    parser_classes = [JSONParser]

    column_names = ['vCONV_CD', 'vCONV_DS', 'vPLAN_CD', 'vPLAN_DS', 'vSUP2_CD']
    table_name = 'V_APP_CONV_PLAN'

    def post(self, request, format=None):
        return self.query_database(self.table_name, self.column_names, request)
    
# Pesquisar convenios disponiveis
class ConvenioDetalhesView(BaseView):
    parser_classes = [JSONParser]

    def post(self, request):
        descricao = request.data.get('descricao', '').strip()
        unidade = request.data.get('unidade', '').strip()

        if not unidade:
            return Response({"data": "A unidade é obrigatória"}, status=status.HTTP_400_BAD_REQUEST)

        convenios = self.buscar_convenio(unidade, descricao)
        if 'error' in convenios:
            return Response({"data": convenios['error']}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        if 'message' in convenios:
            return Response({"data": convenios['message']}, status=status.HTTP_404_NOT_FOUND)

        return Response({"data": convenios}, status=status.HTTP_200_OK)
    
    def buscar_convenio(self, unidade, descricao):
        where_clause = f"UPPER(VUNID_DS) LIKE '%{unidade.upper()}%'"
        if descricao:
            where_clause += f" AND UPPER(VCONV_DS) LIKE '%{descricao.upper()}%'"

        # Verificar se a unidade e opcionalmente o convênio existem
        check_query = f"""
        SET COLSEP '|'
        SELECT COUNT(*) AS COUNT
        FROM V_APP_CONVENIO
        WHERE {where_clause};
        """
        # print("Check convenios query:", check_query)
        check_response = self.query_database(custom_query=check_query, column_names=["COUNT"])
        if check_response.status_code != 200:
            return {"error": "Falha ao buscar dados", "details": check_response.data}

        count_data = check_response.data.get('data', [])
        if not count_data or int(count_data[0]['COUNT']) == 0:
            if descricao:
                return {"message": f"Convênio '{descricao}' na unidade '{unidade}' não encontrado."}
            else:
                return {"message": f"Unidade '{unidade}' não encontrada."}

        # Lista de convenios que tem na unidade escolhida máximo 3
        order_by = "ORDER BY VUNID_DS, VCONV_DS"

        convenios_query = f"""
        SET COLSEP '|'
        SELECT VCONV_CD, VCONV_DS, VREGANS, VUNID_CD, VUNID_DS
        FROM (
            SELECT VCONV_CD, VCONV_DS, VREGANS, VUNID_CD, VUNID_DS,
                ROW_NUMBER() OVER (PARTITION BY VUNID_DS ORDER BY VCONV_DS) AS rn
            FROM V_APP_CONVENIO
            WHERE {where_clause}
        )
        {order_by};
        """
        # print("Convenios query:", convenios_query)
        convenios_response = self.query_database(custom_query=convenios_query, column_names=["VCONV_CD", "VCONV_DS", "VREGANS", "VUNID_CD", "VUNID_DS"])
        if convenios_response.status_code != 200:
            return {"error": "Falha ao buscar dados", "details": convenios_response.data}

        convenios = convenios_response.data.get('data', [])
        if not convenios:
            if descricao:
                return {"message": f"Convênio '{descricao}' na unidade '{unidade}' não encontrado."}
            else:
                return {"message": f"Unidade '{unidade}' não encontrada."}

        resultado = []
        for convenio in convenios:
            vconv_cd = convenio['VCONV_CD']
            planos_query = f"""
            SET COLSEP '|'
            SELECT VPLAN_CD, VPLAN_DS, VSUP2_CD
            FROM (
                SELECT VPLAN_CD, VPLAN_DS, VSUP2_CD, 
                    ROW_NUMBER() OVER (ORDER BY VPLAN_CD) AS row_num
                FROM V_APP_CONV_PLAN
                WHERE VCONV_CD = '{vconv_cd}'
            );
            """
            # print("Planos query para VCONV_CD:", vconv_cd, "é", planos_query)
            planos_response = self.query_database(custom_query=planos_query, column_names=["VPLAN_CD", "VPLAN_DS", "VSUP2_CD"])
            if planos_response.status_code != 200:
                return {"error": "Falha ao buscar dados", "details": planos_response.data}

            planos = planos_response.data.get('data', [])
            if planos:
                convenio['planos'] = planos
            else:
                convenio['planos'] = []
            resultado.append(convenio)

        return resultado



# Busca convênio do paciente consultando CPF 
class BuscarConvenioView(BaseView):
    parser_classes = [JSONParser]

    def post(self, request, format=None):
        cpf = request.data.get('cpf')
        
        if not cpf:
            return Response({"error": "CPF não fornecido"}, status=status.HTTP_200_OK)

        if not self.validar_cpf(cpf):
            return Response({"error": "CPF inválido"}, status=status.HTTP_200_OK)

        logger.info(f"CPF recebido: {cpf}")
        data = self.buscar_convenio(cpf)
        if 'error' in data:
            return Response({"error": data['error']}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        if not data.get('data'):
            return Response({"message": "Nenhum convenio encontrado associado a esse CPF."}, status=status.HTTP_404_NOT_FOUND)

        return Response({"data": data['data']}, status=status.HTTP_200_OK)
    

    def validar_cpf(self, cpf):
        cpf = re.sub(r'\D', '', cpf)
        if len(cpf) != 11 or not cpf.isdigit():
            return False
        for i in range(10):
            if cpf == str(i) * 11:
                return False
        soma = sum(int(cpf[i]) * (10 - i) for i in range(9))
        resto = soma % 11
        digito1 = 0 if resto < 2 else 11 - resto
        soma = sum(int(cpf[i]) * (11 - i) for i in range(10))
        resto = soma % 11
        digito2 = 0 if resto < 2 else 11 - resto
        return cpf[-2:] == f"{digito1}{digito2}"

    def buscar_convenio(self, cpf):

        plsql_block = load_sql_file('buscar_convenio.sql')
        
        # Substituir os placeholders no SQL com os valores reais
        plsql_block = plsql_block.format(cpf=cpf)

        try:
            client = get_ssh_client(settings.HOSTNAME, settings.SSH_PORT, settings.USERNAME, settings.PASSWORD)
            stdin, stdout, stderr = client.exec_command(f"""
            export LD_LIBRARY_PATH={settings.SQLPLUS_PATH}:$LD_LIBRARY_PATH
            export PATH={settings.SQLPLUS_PATH}:$PATH
            echo "{plsql_block}" | sqlplus -S {settings.CONNECTION_STRING}
            """)
            
            errors = stderr.read().decode('utf-8')
            if errors:
                return {"error": errors}
            

            output = stdout.read().decode('utf-8').strip()
            results = []
            current_record = {}
            for line in output.split('\n'):
                if '----- INICIO DOS REGISTROS -----' in line:
                    continue  # Skip the start line
                elif '----- FIM DOS REGISTROS -----' in line:
                    if current_record:
                        results.append(current_record)
                        current_record = {}  # Reset for the next record
                elif ':' in line:
                    key, value = line.split(':', 1)
                    current_record[key.strip()] = value.strip()
                if current_record and 'Produto' in line:  # Assuming 'Produto' is the last item in a record
                    results.append(current_record)
                    current_record = {}  # Reset after each complete record

            if not results:
                return {"message": "Nenhum registro encontrado."}
            return {"data": results}
        finally:
            client.close()

# Busca para validar se o paciente existe
class BuscarPacienteView(APIView):
    parser_classes = [JSONParser]

    def post(self, request, format=None):

        patient_phone = request.data.get('patient_phone')
        logger.debug(f"Paciente_phone recebido: {patient_phone}")

        if not patient_phone:
            return Response({"data": "O número de telefone do paciente é obrigatório"}, status=status.HTTP_400_BAD_REQUEST)
        

        # Remove o código do país se presente
        if patient_phone.startswith('55'):
            patient_phone = patient_phone[2:].strip()

        # Remover qualquer possível espaço ou hífen que possa ter sido deixado
        patient_phone = patient_phone.replace(' ', '').replace('-', '')

        paciente, data_paciente = self.verificar_paciente(patient_phone)
        if paciente is None:
            return Response({"data": "Erro ao verificar paciente"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        if 'error' in paciente:
            return Response({"data": paciente['error']}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        elif not data_paciente:
            return Response({"data": "Paciente não cadastrado."}, status=status.HTTP_200_OK)
        
        return Response({
            "data": data_paciente
        }, status=status.HTTP_200_OK)

    def verificar_paciente(self, patient_phone):
            plsql_block = load_sql_file('buscar_paciente.sql')
        
            # Substituir os placeholders no SQL com os valores reais
            plsql_block = plsql_block.format(patient_phone=patient_phone)
            client = None
            try:

                client = get_ssh_client(settings.HOSTNAME, settings.SSH_PORT, settings.USERNAME, settings.PASSWORD)
                stdin, stdout, stderr = client.exec_command(f"""
                export LD_LIBRARY_PATH={settings.SQLPLUS_PATH}:$LD_LIBRARY_PATH
                export PATH={settings.SQLPLUS_PATH}:$PATH
                echo "{plsql_block}" | sqlplus -S {settings.CONNECTION_STRING}
                """)
                # print(plsql_block)
                errors = stderr.read().decode('utf-8')
                if errors:
                    logger.error(f"Errors during SQL execution: {errors}")
                    return {"error": errors}, None

                output = stdout.read().decode('utf-8').strip()
                logger.debug(f"SQL output: {output}")

                # Processar a saída para criar objetos JSON
                data = {}
                for line in output.split('\n'):
                    if ':' in line:  # Verifica se a linha contém dados
                        key, value = line.split(':', 1)
                        data[key.strip()] = value.strip()

                if not data:  # Se nenhum dado foi adicionado ao dicionário
                    return {}, None

                return {}, data
            except paramiko.SSHException as e:
                logger.error(f"SSHException: {str(e)}")
                return {"error": str(e)}, None # Erro no SSH
            finally:
                if client:
                    client.close()

class CadastrarNovoPaciente(APIView):
    parser_classes = [JSONParser]
    def post(self, request, *args, **kwargs):
        data = request.data
        telefone = request.data.get('telefone')
        idade = request.data.get('Idade')
        cpf = request.data.get('CPF')
        nome = request.data.get('Nome')
        sobrenome = request.data.get('Sobrenome')
        email = request.data.get('Email')

        data_nascimento_formatada = datetime.strptime(data.get('Data de Nascimento'), '%d/%m/%Y').strftime('%Y-%m-%d')

        # Remove o código do país se presente
        if telefone.startswith('55'):
            telefone = telefone[2:].strip()

        # Remover qualquer possível espaço ou hífen que possa ter sido deixado
        telefone = telefone.replace(' ', '').replace('-', '')
        try:
            client = get_ssh_client(settings.HOSTNAME, settings.SSH_PORT, settings.USERNAME, settings.PASSWORD)

            plsql_block = load_sql_file('cadastar_paciente.sql')
            # Substituir os placeholders no SQL com os valores reais
            plsql_block = plsql_block.format(cpf=cpf, idade=idade, nome=nome, sobrenome=sobrenome, email=email,  data_nascimento_formatada=data_nascimento_formatada)

            # Execute the command
            stdin, stdout, stderr = client.exec_command(f"""
            export LD_LIBRARY_PATH={settings.SQLPLUS_PATH}:$LD_LIBRARY_PATH
            export PATH={settings.SQLPLUS_PATH}:$PATH
            echo "{plsql_block}" | sqlplus -S {settings.CONNECTION_STRING}
            """)

            # print(plsql_block)
            output = stdout.read().decode('utf-8', errors='ignore').strip()
            errors = stderr.read().decode('utf-8', errors='ignore').strip()

            output = output.replace('C??digo', 'Código')
                

            if errors:
                return Response({"error": errors}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            # Process the output
            if "Cadastro de paciente realizado com sucesso" in output:
                match = re.search(r'Código BOT gerado: (\d+)', output)
                if match:
                    codigo_bot = match.group(1)
                    return Response({"data": "Cadastro de paciente realizado com sucesso.", "codigo": codigo_bot}, status=status.HTTP_200_OK)
                else:
                    return Response({"data": "Cadastro de paciente realizado com sucesso.", "output": output.replace('\n', ' ')}, status=status.HTTP_200_OK)
            else:
                return Response({"data": "Resposta não reconhecida.", "output": output.replace('\n', ' ')}, status=status.HTTP_200_OK)
        except paramiko.SSHException as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        finally:
            client.close()

class BuscarDataDisponivel(BaseView):
    
    parser_classes = [JSONParser]
    def post(self, request, *args, **kwargs):
        data = request.data
        
        especialidade_mapping = {
            'OFTALMOLOGIA': {'codigo': 1, 'descricao': 'Oftalmologia'},
            'OTORRINOLARINGOLOGIA': {'codigo': 2, 'descricao': 'Otorrinolaringologia'}
        }

        unidade = data.get('unidade', '').upper()
        especialidade = data.get('especialidade', '').upper()
        subespecialidade = data.get('subespecialidade', '').upper()
        data_consulta = data.get('data_consulta', datetime.now().strftime('%d/%m/%Y'))

        unidade_codigo = get_unidade_by_nome(unidade)
        if not unidade_codigo:
            return Response({"error": "Unidade não encontrada."}, status=status.HTTP_400_BAD_REQUEST)

        especialidade_codigo = especialidade_mapping[especialidade]['codigo']

        subespecialidade_query = f"""
        SELECT VSUES_CD FROM v_app_subesp WHERE UPPER(VSUES_DS) = UPPER('{subespecialidade}');
        """

        response = self.query_database(custom_query=subespecialidade_query, column_names=["VSUES_CD"])

        # Verificar se a resposta foi bem-sucedida
        if response.status_code != 200:
            return Response({"error": "Erro ao buscar subespecialidade."}, status=response.status_code)

        subespecialidade_data = response.data.get('data', [])
        # Verificar se dados foram encontrados
        if not subespecialidade_data:
            return Response({"error": f"Subespecialidade '{subespecialidade}' não encontrada."}, status=status.HTTP_404_NOT_FOUND)

        # Acessar o código da subespecialidade
        subespecialidade_cd = subespecialidade_data[0]['VSUES_CD']
        # print(f"subespecialidade {subespecialidade} tem código {subespecialidade_cd}")

        try:
            data_consulta_obj = datetime.strptime(data_consulta, '%d/%m/%Y')
            if data_consulta_obj.date() < datetime.now().date():
                return Response({"data": "Data de consulta inválida ou anterior à data atual."}, status=status.HTTP_400_BAD_REQUEST)
            data_formatada = data_consulta_obj.strftime('%Y-%m-%d')
        except ValueError:
            return Response({"data": "Formato de data inválido. Use 'DD/MM/YYYY'."}, status=status.HTTP_400_BAD_REQUEST)
        
        plsql_block = load_sql_file('buscar_data_disponivel.sql')
        plsql_block = plsql_block.format(unidade_codigo=unidade_codigo, especialidade_codigo=especialidade_codigo, subespecialidade_cd=subespecialidade_cd, data_formatada=data_formatada)


        try:
            client = get_ssh_client(settings.HOSTNAME, settings.SSH_PORT, settings.USERNAME, settings.PASSWORD)
            stdin, stdout, stderr = client.exec_command(f"""
            export LD_LIBRARY_PATH={settings.SQLPLUS_PATH}:$LD_LIBRARY_PATH
            export PATH={settings.SQLPLUS_PATH}:$PATH
            echo "{plsql_block}" | sqlplus -S {settings.CONNECTION_STRING}
            """)
            
            errors = stderr.read().decode('utf-8')
            if errors:
                return {"error": errors}, None
            
            output = stdout.read().decode('utf-8', errors='ignore').strip()
            
            # Processamento de saída melhorado
            results = []
            current_data = {}
            for line in output.split('\n'):
                if '-----' in line:  # Indica o início/fim de um registro
                    if current_data:
                        results.append(current_data)
                        current_data = {}
                else:
                    parts = line.split(':', 1)
                    if len(parts) == 2:
                        key, value = parts
                        current_data[key.strip()] = value.strip()

            if current_data:  # Adicionar o último registro se houver
                results.append(current_data)

            if not results:
                return Response({"data": "Nenhuma data disponível encontrada."}, status=status.HTTP_404_NOT_FOUND)


            # Agrupar resultados por médico
            grouped_results = {}
            for result in results:
                medico_id = result.get('VCOCL_CD', 'Não especificado')
                if medico_id not in grouped_results:
                    grouped_results[medico_id] = {
                        "Unidade": get_unidade_by_codigo(unidade_codigo),
                        "CRM Médico": medico_id,
                        "Nome do Médico": result.get('VCOCL_NM', 'Não especificado'),
                        "Tipo de Consulta": result.get('VGPRO_DS', 'Consulta'),
                        "Especialidade": result.get('VPRRE_DS', 'Não especificado'),
                        "Sub-Especialidade": result.get('VSUES_DS', 'Não especificado'),
                        "Datas Disponíveis": set()
                    }
                grouped_results[medico_id]["Datas Disponíveis"].add(
                    result.get('VAGEN_DT', 'Não especificado')
                )

            # Convertendo conjuntos de datas para listas
            for medico in grouped_results.values():
                medico["Datas Disponíveis"] = list(medico["Datas Disponíveis"])

            final_results = list(grouped_results.values())
            return Response({"data": final_results}, status=status.HTTP_200_OK)
            #return Response({"data": results}, status=status.HTTP_200_OK)        
        except paramiko.SSHException as e:
            return Response({"error": {"code": -1, "message": str(e), "timestamp": datetime.datetime.now().isoformat()}}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        finally:
            if client:
                client.close()

class BuscarHorario(BaseView):

    parser_classes = [JSONParser]

    def query_database(self, custom_query=None, column_names=None):
        return super().query_database(custom_query=custom_query, column_names=column_names)

    def post(self, request, *args, **kwargs):
        data = request.data

        especialidade_mapping = {
            'OFTALMOLOGIA': {'codigo': 1, 'descricao': 'Oftalmologia'},
            'OTORRINOLARINGOLOGIA': {'codigo': 2, 'descricao': 'Otorrinolaringologia'}
        }


        crm_medico = data.get('crm_medico', 'NULL')
        unidade = data.get('unidade', '').upper()
        vprre_codigo = 1 # consulta
        especialidade = data.get('especialidade', '').upper()
        sub_especialidade = data.get('sub_especialidade', '').upper()
        data_consulta = data.get('data_consulta', datetime.now().strftime('%d/%m/%Y'))

         # Converting data_consulta from string to datetime object
        try:
            data_consulta_obj = datetime.strptime(data_consulta, '%d/%m/%Y')
            data_formatada = data_consulta_obj.strftime('%Y-%m-%d')
        except ValueError:
            return Response({"error": "Formato de data inválido. Use 'DD/MM/YYYY'."}, status=status.HTTP_400_BAD_REQUEST)
       
        unidade_codigo = get_unidade_by_nome(unidade)
        if not unidade_codigo:
            return Response({"error": "Unidade não encontrada."}, status=status.HTTP_400_BAD_REQUEST)

        especialidade_codigo = especialidade_mapping[especialidade]['codigo']
        

        subespecialidade_query = f"""
        SELECT VSUES_CD FROM v_app_subesp WHERE UPPER(VSUES_DS) = UPPER('{sub_especialidade}');
        """

        response = self.query_database(custom_query=subespecialidade_query, column_names=["VSUES_CD"])

        # Verificar se a resposta foi bem-sucedida
        if response.status_code != 200:
            return Response({"error": "Erro ao buscar subespecialidade."}, status=response.status_code)

        subespecialidade_data = response.data.get('data', [])
        # Verificar se dados foram encontrados
        if not subespecialidade_data:
            return Response({"error": f"Subespecialidade '{sub_especialidade}' não encontrada."}, status=status.HTTP_404_NOT_FOUND)

        # Acessar o código da subespecialidade
        subespecialidade_cd = subespecialidade_data[0]['VSUES_CD']
        logger.info(f"subespecialidade {sub_especialidade} tem código {subespecialidade_cd}")
        
        if crm_medico:
            crm_medico_clause = f"p_vcocd_cd NUMBER := {crm_medico}"
        else:
            crm_medico_clause = "p_vcocd_cd NUMBER := NULL"
        # Estabelece conexão SSH e executa o bloco PL/SQL
        try:
            
            plsql_block = load_sql_file('buscar_horario.sql')
            # Substituir os placeholders no SQL com os valores reais
            plsql_block = plsql_block.format(unidade_codigo=unidade_codigo, vprre_codigo=vprre_codigo, especialidade_codigo=especialidade_codigo, subespecialidade_cd=subespecialidade_cd, data_formatada=data_formatada, crm_medico_clause=crm_medico_clause)

            client = get_ssh_client(settings.HOSTNAME, settings.SSH_PORT, settings.USERNAME, settings.PASSWORD)
            stdin, stdout, stderr = client.exec_command(f"""
            export LD_LIBRARY_PATH={settings.SQLPLUS_PATH}:$LD_LIBRARY_PATH
            export PATH={settings.SQLPLUS_PATH}:$PATH
            echo "{plsql_block}" | sqlplus -S {settings.CONNECTION_STRING}
            """)

            logger.info(plsql_block)
            
            output = stdout.read().decode().strip()
            errors = stderr.read().decode().strip()
            if errors:
                return Response({"error": errors}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            # Processa a saída para extrair informações
            
            results = self.parse_output(output)
            if not results:
                return Response({"data": "Nenhum horário disponível para os critérios selecionados."}, status=status.HTTP_200_OK)

            return Response({"data": results}, status=status.HTTP_200_OK)  # Retorna diretamente os resultados
        except paramiko.SSHException as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        finally:
            client.close()

    def parse_output(self, output):
        results = []
        current_medico = None
        medico_map = {}

        lines = output.split('\n')
        for line in lines:
            if 'Unidade' in line and 'DS:' in line:
                unidade = line.split('DS: ')[1].strip()
                if unidade not in medico_map:
                    medico_map[unidade] = {}
            elif 'Codigo Local CD' in line and 'NM:' in line:
                nome_medico = line.split('NM: ')[1].strip()
                if unidade not in medico_map:
                    medico_map[unidade] = {}
                if nome_medico not in medico_map[unidade]:
                    medico_map[unidade][nome_medico] = {
                        "Nome Médico": nome_medico,
                        "Unidade": unidade,
                        "Horários": [],
                        "Data Agendamento": ""
                    }
                current_medico = medico_map[unidade][nome_medico]
            elif 'Data Agendamento' in line:
                data_agendamento = line.split(': ')[1].strip()
                current_medico["Data Agendamento"] = data_agendamento
            elif 'Hora HH' in line:
                hora = line.split(': ')[1].strip()
                current_medico["Horários"].append(hora)

        for unidade in medico_map:
            for medico in medico_map[unidade]:
                results.append(medico_map[unidade][medico])

        if not results:
            return {"data": "Nenhum horário disponível para os critérios selecionados."}

        return results



class RealizarAgendamento(BaseView):
    parser_classes = [JSONParser]

    def query_database(self, custom_query=None, column_names=None):
        return super().query_database(custom_query=custom_query, column_names=column_names)


    def post(self, request, *args, **kwargs):
        data = request.data


        especialidade_mapping = {
            'OFTALMOLOGIA': {'codigo': 1, 'descricao': 'Oftalmologia'},
            'OTORRINOLARINGOLOGIA': {'codigo': 2, 'descricao': 'Otorrinolaringologia'}
        }


        crm_medico = data.get('crm_medico', 'Não especificado') # p_vcocl_cd
        unidade = data.get('unidade', '').upper() #p_vunid_cd
        vconsulta = 1 # consulta
        especialidade = data.get('especialidade', '').upper()
        sub_especialidade = data.get('sub_especialidade', '').upper()
        descricao_convenio = data.get('convenio', 'Não especificado').upper()
        descricao_plano = data.get('plano', 'Não especificado') # p_vpla2_c
        data_consulta = data.get('data_consulta', datetime.now().strftime('%d/%m/%Y')) # p_vdt
        hora_agenda = data.get('hora_agenda', 'Não especificado')
        minuto_agenda = data.get('minuto_agenda', 'Não especificado')
        cpf = data.get('cpf', 'Não especificado')
        

         # Converting data_consulta from string to datetime object
        try:
            data_consulta_obj = datetime.strptime(data_consulta, '%d/%m/%Y')
            data_formatada = data_consulta_obj.strftime('%Y-%m-%d')
        except ValueError:
            return Response({"data": "Formato de data inválido. Use 'DD/MM/YYYY'."}, status=status.HTTP_400_BAD_REQUEST)

        unidade_codigo = get_unidade_by_nome(unidade)
        if not unidade_codigo:
            return Response({"error": "Unidade não encontrada."}, status=status.HTTP_400_BAD_REQUEST)

        especialidade_codigo = especialidade_mapping[especialidade]['codigo']

        subespecialidade_query = f"""
        SELECT VSUES_CD FROM v_app_subesp WHERE UPPER(VSUES_DS) = UPPER('{sub_especialidade}');
        """

        response = self.query_database(custom_query=subespecialidade_query, column_names=["VSUES_CD"])

        # Verificar se a resposta foi bem-sucedida
        if response.status_code != 200:
            return Response({"data": "Erro ao buscar subespecialidade."}, status=response.status_code)

        subespecialidade_data = response.data.get('data', [])
        # Verificar se dados foram encontrados
        if not subespecialidade_data:
            return Response({"data": f"Subespecialidade '{sub_especialidade}' não encontrada."}, status=status.HTTP_404_NOT_FOUND)

        # Acessar o código da subespecialidade
        subespecialidade_cd = subespecialidade_data[0]['VSUES_CD']
        logger.info(f"subespecialidade {sub_especialidade} tem código {subespecialidade_cd}")

        # Obtem código do convenio
        convenio_query = f"""
        SELECT VCONV_CD FROM V_APP_CONVENIO WHERE UPPER(VCONV_DS) = UPPER('{descricao_convenio}');
        """
        response = self.query_database(custom_query=convenio_query, column_names=["VCONV_CD"])

        # Verificar se a resposta foi bem-sucedida
        if response.status_code != 200:
            return Response({"data": "Erro ao buscar convenio."}, status=response.status_code)

        convenio_data = response.data.get('data', [])

        if not convenio_data:
            return Response({"data": f"Convenio {descricao_convenio} não encontrado"}, status=400)
        
        convenio_cd = convenio_data[0]['VCONV_CD']
        logger.info(f"Convenio {descricao_convenio} tem codigo {convenio_cd}")

        # Obter código do plano/subplano pelo código de convênio
        plano_query = f"""
        SET COLSEP '|'
        SELECT VPLAN_CD, VSUP2_CD FROM V_APP_CONV_PLAN WHERE VCONV_CD = {convenio_cd} AND UPPER(VPLAN_DS) = UPPER('{descricao_plano}');
        """
        response = self.query_database(custom_query=plano_query, column_names=["VPLAN_CD", "VSUP2_CD"])
        # Verificar se a resposta foi bem-sucedida
        if response.status_code != 200:
            return Response({"data": "Erro ao buscar plano."}, status=response.status_code)

        plano_data = response.data.get('data', [])
        
        if not plano_data:
            return Response({"data": f"Plano {descricao_plano} não encontrado"}, status=400)
        
        plano_cd, subplano_cd = plano_data[0]['VPLAN_CD'], plano_data[0]['VSUP2_CD']
        logger.info(f'Codigo do plano {descricao_plano}: {plano_cd}')
        logger.info(f'Codigo do subplano: {subplano_cd}')

        client = None
        try:            
            # Montagem do comando PL/SQL a ser executado
            plsql_command = load_sql_file('realizar_agendamento.sql')
        
            # Substituir os placeholders no SQL com os valores reais
            plsql_command = plsql_command.format(
                unidade_codigo=unidade_codigo,
                vconsulta=vconsulta,
                especialidade_codigo=especialidade_codigo,
                subespecialidade_cd=subespecialidade_cd,
                convenio_cd=convenio_cd,
                plano_cd=plano_cd,
                subplano_cd=subplano_cd,
                data_formatada=data_formatada,
                hora_agenda=hora_agenda,
                minuto_agenda=minuto_agenda,
                crm_medico=crm_medico,
                cpf=cpf
            )

            client = get_ssh_client(settings.HOSTNAME, settings.SSH_PORT, settings.USERNAME, settings.PASSWORD)
            stdin, stdout, stderr = client.exec_command(f"""
            export LD_LIBRARY_PATH={settings.SQLPLUS_PATH}:$LD_LIBRARY_PATH
            export PATH={settings.SQLPLUS_PATH}:$PATH
            echo "{plsql_command}" | sqlplus -S {settings.CONNECTION_STRING}
            """)

            logger.info(plsql_command)

            output = stdout.read().decode().strip()
            errors = stderr.read().decode().strip()

            if errors:
                return Response({"data": errors}, status=status.HTTP_400_BAD_REQUEST)
            
            output = output.replace('C??digo', 'Código').strip()
            clean_output = ' '.join(output.replace('\r', '').split())

            # Regex mais flexível para capturar partes variáveis do output
            error_regex = re.compile(
                r"Erro: (?P<error_desc>.+?) Und:(?P<unit>\w+)Crm:(?P<crm>\d+)-(?P<doctor_name>[^V]+?) V SASSO-(?P<date>\d{2}/\d{2}/\d{4}) Hr:(?P<time>\d{2}:\d{2}) Código de Erro: (?P<error_code>\d+) Código de Agendamento: (?P<agend_code>\d*)",
                re.IGNORECASE | re.DOTALL
            )
            match = error_regex.search(clean_output)

            if match:
                data = match.groupdict()
                data['agend_code'] = data['agend_code'] if data['agend_code'] else "0"  # Define '0' se vazio

                response_data = {
                    "Erro": data['error_desc'],
                    "Unidade": data['unit'],
                    "CRM": data['crm'],
                    "Nome do Médico": data['doctor_name'].strip(),
                    "Data Consulta": data['date'],
                    "Horário Consulta": data['time'],
                    "Código de Erro": data['error_code'],
                    "Código de Agendamento": data['agend_code']
                }
                return JsonResponse(response_data, status=400)

            return JsonResponse({"data": clean_output}, status=200)
        except Exception as e:
            return Response({"data": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        finally:
            if client:
                client.close()


class CadastrarNovoConveio(BaseView):
    # app_agd.GERA_PAC_BOT_CNV
    parser_classes = [JSONParser]

    def query_database(self, custom_query=None, column_names=None):
        return super().query_database(custom_query=custom_query, column_names=column_names)


    def post(self, request, *args, **kwargs):
        data = request.data

        descricao_convenio = data.get('convenio', 'Não especificado').upper()
        descricao_plano = data.get('plano', 'Não especificado')
        cpf = data.get('cpf', 'Não especificado')

        # Obtem código do convenio atraves da descrição
        convenio_query = f"""
        SELECT VCONV_CD FROM V_APP_CONVENIO 
        WHERE UPPER(REPLACE(VCONV_DS, ' ', '')) = UPPER(REPLACE('{descricao_convenio}', ' ', ''));
        """
        response = self.query_database(custom_query=convenio_query, column_names=["VCONV_CD"])

        # Verificar se a resposta foi bem-sucedida
        if response.status_code != 200:
            return Response({"data": "Erro ao buscar convenio."}, status=response.status_code)

        convenio_data = response.data.get('data', [])

        if not convenio_data:
            return Response({"data": f"Convenio {descricao_convenio} não encontrado"}, status=400)
        
        convenio_cd = convenio_data[0]['VCONV_CD']
        logger.info(f"Convenio {descricao_convenio} tem codigo {convenio_cd}")

        # Obter código do plano/subplano pelo código de convênio
        plano_query = f"""
        SET COLSEP '|'
        SELECT VPLAN_CD, VSUP2_CD FROM V_APP_CONV_PLAN 
        WHERE VCONV_CD = {convenio_cd} 
        AND UPPER(REPLACE(VPLAN_DS, ' ', '')) = UPPER(REPLACE('{descricao_plano}', ' ', ''));
        """
        # print(plano_query)
        response = self.query_database(custom_query=plano_query, column_names=["VPLAN_CD", "VSUP2_CD"])
        # Verificar se a resposta foi bem-sucedida
        if response.status_code != 200:
            return Response({"data": "Erro ao buscar plano."}, status=response.status_code)

        plano_data = response.data.get('data', [])
        
        if not plano_data:
            return Response({"data": f"Plano {descricao_plano} não encontrado"}, status=400)
        
        plano_cd = plano_data[0]['VPLAN_CD']
        logger.info(f'Codigo do plano {descricao_plano}: {plano_cd}')

        client = None
        try:            
            # Montagem do comando PL/SQL a ser executado
            plsql_block = load_sql_file('cadastrar_convenio.sql')
            # Substituir os placeholders no SQL com os valores reais
            plsql_block = plsql_block.format(convenio_cd=convenio_cd, plano_cd=plano_cd, cpf=cpf)

            client = get_ssh_client(settings.HOSTNAME, settings.SSH_PORT, settings.USERNAME, settings.PASSWORD)
            stdin, stdout, stderr = client.exec_command(f"""
            export LD_LIBRARY_PATH={settings.SQLPLUS_PATH}:$LD_LIBRARY_PATH
            export PATH={settings.SQLPLUS_PATH}:$PATH
            echo "{plsql_block}" | sqlplus -S {settings.CONNECTION_STRING}
            """)

            output = stdout.read().decode().strip()
            errors = stderr.read().decode().strip()

            # print(plsql_command)

            if errors:
                return Response({"error": errors}, status=status.HTTP_400_BAD_REQUEST)

            
            # Clean up the output message more aggressively
            cleaned_output = re.sub(r'PL/SQL procedure successfully completed.', '', output)
            cleaned_output = re.sub(r'\n+', ' ', cleaned_output)  # Remove multiple newlines
            cleaned_output = cleaned_output.strip()


            return Response({"data": cleaned_output}, status=status.HTTP_200_OK)   
        except Exception as e:
            return Response({"data": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        finally:
            if client:
                client.close()

class CancelarConsultaView(BaseView):
    parser_classes = [JSONParser]

    def post(self, request):
        patient_id = request.data.get('cpf')
        cd_agendam = request.data.get('codigo_agendamento')

        if not patient_id or not cd_agendam:
            return Response({"data": "Os parâmetros 'de CPF' e 'código agendamento' são obrigatórios."}, status=status.HTTP_400_BAD_REQUEST)

        cancelamento = self.cancelar_consulta(patient_id, cd_agendam)
        if 'error' in cancelamento:
            return Response({"data": cancelamento['error']}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        if 'message' in cancelamento:
            return Response({"data": cancelamento['message']}, status=status.HTTP_404_NOT_FOUND)

        return Response({"data": cancelamento['message']}, status=status.HTTP_200_OK)
    
    def cancelar_consulta(self, patient_id, cd_agendam):
        #print("Cancelar consulta PL/SQL block:", plsql_block)

        plsql_block = load_sql_file('cancelar_consultas.sql')
        
          # Substituir os placeholders no SQL com os valores reais
        plsql_block = plsql_block.format(patient_id=patient_id, cd_agendam=cd_agendam)

        try:
            client = get_ssh_client(settings.HOSTNAME, settings.SSH_PORT, settings.USERNAME, settings.PASSWORD)
            stdin, stdout, stderr = client.exec_command(f"""
            export LD_LIBRARY_PATH={settings.SQLPLUS_PATH}:$LD_LIBRARY_PATH
            export PATH={settings.SQLPLUS_PATH}:$PATH
            echo "{plsql_block}" | sqlplus -S {settings.CONNECTION_STRING}
            """)
            output = stdout.read().decode().strip()
            errors = stderr.read().decode().strip()

            if errors:
                return {"error": errors}

            # Processa a saída para determinar o resultado
            if 'Cancelamento realizado com sucesso' in output:
                message = f"Cancelamento realizado com sucesso para o agendamento: {cd_agendam}"
            else:
                message = f"Erro ao tentar cancelar o agendamento: {cd_agendam}"

            return {"message": message}
        except paramiko.SSHException as e:
            return {"error": str(e)}
        finally:
            client.close()


class VerConsultasFuturasView(BaseView):
    parser_classes = [JSONParser]

    def post(self, request):
        patient_id = request.data.get('cpf')
        vgpro_cd = 1
        vprre_cd = request.data.get('especialidade')

        if not patient_id or not vgpro_cd or not vprre_cd:
            return Response({"data": "Os parâmetros 'cpf' e 'especialidade' são obrigatórios."}, status=status.HTTP_400_BAD_REQUEST)

        consultas = self.ver_consultas_futuras(patient_id, vgpro_cd, vprre_cd)
        if 'error' in consultas:
            return Response({"data": consultas['error']}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        if 'message' in consultas:
            return Response({"data": consultas['message']}, status=status.HTTP_404_NOT_FOUND)

        return Response({"data": consultas}, status=status.HTTP_200_OK)

    def ver_consultas_futuras(self, patient_id, vgpro_cd, vprre_cd):
        plsql_block = load_sql_file('ver_consultas_futuras.sql')
        
        # Substituir os placeholders no SQL com os valores reais
        plsql_block = plsql_block.format(patient_id=patient_id, vgpro_cd=vgpro_cd, vprre_cd=vprre_cd)

        try:
            client = get_ssh_client(settings.HOSTNAME, settings.SSH_PORT, settings.USERNAME, settings.PASSWORD)
            stdin, stdout, stderr = client.exec_command(f"""
            export LD_LIBRARY_PATH={settings.SQLPLUS_PATH}:$LD_LIBRARY_PATH
            export PATH={settings.SQLPLUS_PATH}:$PATH
            echo "{plsql_block}" | sqlplus -S {settings.CONNECTION_STRING}
            """)
            output = stdout.read().decode().strip()
            errors = stderr.read().decode().strip()

            if errors:
                return {"error": errors}

            # Processa a saída para determinar o resultado
            consultas = self.parse_consultas_futuras(output)
            if not consultas:
                return {"message": "Nenhuma consulta futura encontrada."}

            return consultas
        except paramiko.SSHException as e:
            return {"error": str(e)}
        finally:
            client.close()

    def parse_consultas_futuras(self, output):
        results = []
        current_consulta = {}

        lines = output.split('\n')
        for line in lines:
            line = line.strip()
            if line.startswith('Unidade_CD:'):
                if current_consulta:  # Adiciona a consulta atual ao resultado se já houver dados
                    results.append(current_consulta)
                    current_consulta = {}  # Reinicia o dicionário para a próxima consulta
                unidade_cd = line.split(':', 1)[1].strip()
                unidade_nome = get_unidade_by_codigo(unidade_cd)
                current_consulta["Unidade"] = unidade_nome
            elif line.startswith('Medico:'):
                current_consulta["Médico"] = line.split(':', 1)[1].strip()
            elif line.startswith('Data:'):
                current_consulta["Data"] = line.split(':', 1)[1].strip()
            elif line.startswith('Hora:'):
                current_consulta["Hora"] = line.split(':', 1)[1].strip()
            elif line.startswith('Agendamento_CD:'):
                current_consulta["Agendamento CD"] = line.split(':', 1)[1].strip()
            elif line == '---':
                if current_consulta:  # Adiciona a consulta atual ao resultado quando o marcador de fim é encontrado
                    results.append(current_consulta)
                    current_consulta = {}  # Reinicia o dicionário para a próxima consulta

        if current_consulta:  # Adiciona a última consulta se houver
            results.append(current_consulta)

        if not results:  # Se não encontrou nenhuma consulta
            return "Nenhuma consulta futura encontrada."
        else:
            return results  # Usa "data" como chave principal