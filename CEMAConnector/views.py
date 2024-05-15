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
import logging

logger = logging.getLogger('django')


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
        hostname = config('HOSTNAME')
        ssh_port = config('SSH_PORT', cast=int)
        username = config('USERNAME_ORACLE')
        password = config('PASSWORD')
        sqlplus_path = config('SQLPLUS_PATH')
        connection_string = config('CONNECTION_STRING')

        if custom_query:
            plsql_block = custom_query
            logger.info(f"executando custom query {plsql_block}")
        else:    
            filters = request.data.get('filters', {})
            where_clause = " AND ".join([f"{column} = '{value}'" for column, value in filters.items() if column in column_names])

            plsql_block = f"""
            SET PAGESIZE 0
            SET FEEDBACK OFF
            SET VERIFY OFF
            SET HEADING OFF
            SET ECHO OFF
            SET LINESIZE 32767
            SET TRIMSPOOL ON
            SET COLSEP '|'
            SELECT {", ".join(column_names)}
            FROM {table_name}
            {f'WHERE {where_clause}' if where_clause else ''};
            EXIT;
            """

        try:
            client = get_ssh_client(hostname, ssh_port, username, password)
            stdin, stdout, stderr = client.exec_command(f"""
            export LD_LIBRARY_PATH={sqlplus_path}:$LD_LIBRARY_PATH
            export PATH={sqlplus_path}:$PATH
            echo "{plsql_block}" | sqlplus -S {connection_string}
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
    column_names = ['VGPRO_CD', 'VGPRO_DS', 'VPRRE_CD', 'VPRRE_DS', 'VSUES_CD', 'VSUES_DS', 'VVOX', 'VTODOS']
    table_name = 'v_app_subesp'

    def post(self, request, format=None):
        return self.query_database(self.table_name, self.column_names, request)

class UnidView(BaseView):

    parser_classes = [JSONParser]

    column_names = ['VUNID_CD', 'VUNID_DS', 'VLOGRADOURO', 'VNR', 'VCOMPL', 'VBAIRRO', 'VCIDADE', 'VCEP', 'VUF', 'VDDD', 'VTEL', 'VRAMAL', 'VUNID_APRES', 'VUNID_LOCAL']
    table_name = 'V_APP_UNID'

    def post(self, request, format=None):
        unidade = request.data.get('unidade', '').strip()

        if unidade:
            where_clause = f"UPPER(VUNID_DS) LIKE '%{unidade.upper()}%'"
            order_by = "ORDER BY VUNID_DS"  # Ordenar por descrição da unidade
        else:
            where_clause = "VUNID_DS IN ('BELEM', 'ITAQUERA', 'ARICANDUVA')"
            order_by = "ORDER BY VUNID_DS"  # Ordenar por unidades especificadas

        unid_query = f"""
        SET LINESIZE 32767
        SET PAGESIZE 50000
        SET COLSEP '|'
        SET TRIMSPOOL ON
        SET WRAP OFF
        SELECT VUNID_CD, VUNID_DS, VLOGRADOURO, VNR, VCOMPL, VBAIRRO, VCIDADE, VCEP, VUF, VDDD, VTEL, VRAMAL, VUNID_APRES, VUNID_LOCAL
        FROM (
            SELECT VUNID_CD, VUNID_DS, VLOGRADOURO, VNR, VCOMPL, VBAIRRO, VCIDADE, VCEP, VUF, VDDD, VTEL, VRAMAL, VUNID_APRES, VUNID_LOCAL,
                   ROW_NUMBER() OVER (PARTITION BY VUNID_DS ORDER BY VUNID_DS) AS rn
            FROM {self.table_name}
            WHERE {where_clause}
        )
        WHERE rn <= 3
        {order_by};
        """

        logger.info(f"Executando consulta {unid_query}")
        # Executa a consulta no banco de dados
        unid_response = self.query_database(custom_query=unid_query, column_names=["VUNID_CD", "VUNID_DS", "VLOGRADOURO", "VNR", "VCOMPL", "VBAIRRO", "VCIDADE", "VCEP", "VUF", "VDDD", "VTEL", "VRAMAL", "VUNID_APRES", "VUNID_LOCAL",])
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

    def query_database(self, custom_query=None, column_names=None):
        return super().query_database(custom_query=custom_query, column_names=column_names)

    def post(self, request):
        descricao = request.data.get('descricao', '').strip()

        if descricao:
            where_clause = f"UPPER(VCONV_DS) LIKE '%{descricao.upper()}%'"
            order_by = "ORDER BY VCONV_DS"  # ordenar por descrição quando a busca é feita por descrição
        else:
            where_clause = "VUNID_DS IN ('BELEM', 'ITAQUERA', 'ARICANDUVA')"
            order_by = "ORDER BY VUNID_DS, VCONV_DS"  # ordenar por unidade e descrição para agrupar corretamente

        convenios_query = f"""
        SET COLSEP '|'
        SELECT VCONV_CD, VCONV_DS, VREGANS, VUNID_CD, VUNID_DS
        FROM (
            SELECT VCONV_CD, VCONV_DS, VREGANS, VUNID_CD, VUNID_DS,
                ROW_NUMBER() OVER (PARTITION BY VUNID_DS ORDER BY VCONV_DS) AS rn
            FROM V_APP_CONVENIO
            WHERE {where_clause}
        )
        WHERE rn <= 3
        {order_by if descricao else ''};
        """

        # Executa a consulta no banco de dados via SSH
        convenios_response = self.query_database(custom_query=convenios_query, column_names=["VCONV_CD", "VCONV_DS", "VREGANS", "VUNID_CD", "VUNID_DS"])
        if convenios_response.status_code != 200:
            return convenios_response

        convenios = convenios_response.data.get('data', [])
        # Itera pelos convênios para buscar os planos relacionados
        resultado = []
        for convenio in convenios:
            vconv_cd = convenio['VCONV_CD']
            planos_query = f"""
            SET COLSEP '|'
            SELECT VPLAN_CD, VPLAN_DS, VSUP2_CD
            FROM V_APP_CONV_PLAN
            WHERE VCONV_CD = '{vconv_cd}';
            """
            planos_response = self.query_database(custom_query=planos_query, column_names=["VPLAN_CD", "VPLAN_DS", "VSUP2_CD"])
            if planos_response.status_code != 200:
                return planos_response
            
            planos = planos_response.data.get('data', [])
            convenio['planos'] = planos
            resultado.append(convenio)

        return Response({"data": resultado}, status=status.HTTP_200_OK)


# Busca convênio do paciente consultando CPF 
class BuscarConvenioView(BaseView):
    parser_classes = [JSONParser]

    def post(self, request, format=None):
        cpf = request.data.get('cpf')
        if not cpf:
            return Response({"error": "CPF não fornecido"}, status=status.HTTP_400_BAD_REQUEST)

        if not self.validar_cpf(cpf):
            return Response({"error": "CPF inválido"}, status=status.HTTP_400_BAD_REQUEST)

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
        plsql_block = f"""
        SET SERVEROUTPUT ON SIZE UNLIMITED;
        DECLARE
            p_erro BOOLEAN := FALSE;
            p_erro_cd NUMBER;
            p_erro_mt VARCHAR2(4000);
            p_obs VARCHAR2(4000);
            p_obs_part VARCHAR2(4000);
            p_possui_pac VARCHAR2(10);
            p_possui_part VARCHAR2(10);
            p_possui_conv VARCHAR2(10);
            p_recordset SYS_REFCURSOR;
            p_origem VARCHAR2(100) := 'C';
            p_patient_id NUMBER := {cpf};  

            v_tp VARCHAR2(20);
            v_cd_conv NUMBER;
            v_convenio VARCHAR2(100);
            v_cd_plano NUMBER;
            v_plano VARCHAR2(100);
            v_produto VARCHAR2(100);

        BEGIN
        app_agd.BUSCAR_PAC_BOT_CONV(
            P_ERRO          => p_erro,
            P_ERRO_CD       => p_erro_cd,
            P_ERRO_MT       => p_erro_mt,
            P_OBS           => p_obs,
            P_OBS_PART      => p_obs_part,
            P_POSSUI_PAC    => p_possui_pac,
            P_POSSUI_PART   => p_possui_part,
            P_POSSUI_CONV   => p_possui_conv,
            P_RECORDSET     => p_recordset,
            P_ORIGEM        => p_origem,
            P_PATIENT_ID    => p_patient_id
        );

        DBMS_OUTPUT.PUT_LINE('----- INICIO DOS REGISTROS -----');
        LOOP
            FETCH p_recordset INTO v_tp, v_cd_conv, v_convenio, v_cd_plano, v_plano, v_produto;
            EXIT WHEN p_recordset%NOTFOUND;
            DBMS_OUTPUT.PUT_LINE('Tipo: ' || v_tp);
            DBMS_OUTPUT.PUT_LINE('Codigo Convenio: ' || v_cd_conv);
            DBMS_OUTPUT.PUT_LINE('Convenio: ' || v_convenio);
            DBMS_OUTPUT.PUT_LINE('Codigo Plano: ' || v_cd_plano);
            DBMS_OUTPUT.PUT_LINE('Plano: ' || v_plano);
            DBMS_OUTPUT.PUT_LINE('Produto: ' || v_produto);
        END LOOP;
        DBMS_OUTPUT.PUT_LINE('----- FIM DOS REGISTROS -----');

        CLOSE p_recordset;

        IF p_erro THEN
            DBMS_OUTPUT.PUT_LINE('Erro: ' || TO_CHAR(p_erro_cd) || ' - ' || p_erro_mt);
        END IF;

        END;
        /
        """
        try:
            client = get_ssh_client(config('HOSTNAME'), config('SSH_PORT', cast=int), config('USERNAME_ORACLE'), config('PASSWORD'))
            stdin, stdout, stderr = client.exec_command(f"""
            export LD_LIBRARY_PATH={config('SQLPLUS_PATH')}:$LD_LIBRARY_PATH
            export PATH={config('SQLPLUS_PATH')}:$PATH
            echo "{plsql_block}" | sqlplus -S {config('CONNECTION_STRING')}
            """)
            errors = stderr.read().decode('utf-8')
            if errors:
                return {"error": errors}

            output = stdout.read().decode('utf-8').strip()
            data = {}
            for line in output.split('\n'):
                if ':' in line:
                    key, value = line.split(':', 1)
                    data[key.strip()] = value.strip()
            return {"data": data}

        finally:
            client.close()

# Busca para validar se o paciente existe
class BuscarPacienteView(APIView):
    parser_classes = [JSONParser]

    def post(self, request, format=None):
        patient_phone = request.data.get('patient_phone')
        if not patient_phone:
            return Response({"error": "O número de telefone do paciente é obrigatório"}, status=status.HTTP_400_BAD_REQUEST)

        logger.info("Paciente_phone recebido:", patient_phone)  # Debugging

        paciente, data_paciente = self.verificar_paciente(patient_phone)
        if paciente is None:
            return Response({"error": "Erro ao verificar paciente"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        if 'error' in paciente:
            return Response({"error": paciente['error']}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        elif not data_paciente:
            return Response({"message": "Paciente não cadastrado."}, status=status.HTTP_404_NOT_FOUND)
        
        return Response({
            "paciente": data_paciente
        }, status=status.HTTP_200_OK)

    def verificar_paciente(self, patient_phone):
            plsql_block = f"""
            SET SERVEROUTPUT ON SIZE UNLIMITED;

            DECLARE
            p_erro BOOLEAN := FALSE;
            p_erro_cd NUMBER;
            p_erro_mt VARCHAR2(4000);
            p_recordset SYS_REFCURSOR;
            p_origem VARCHAR2(100) := 'C';
            p_patient_phone VARCHAR2(100) := '{patient_phone}';
            p_patient_id NUMBER := NULL;

            v_cd_app NUMBER;
            v_nome VARCHAR2(100);
            v_dt_nasc DATE;
            v_sexo VARCHAR2(1);
            v_telefone VARCHAR2(20);
            v_email VARCHAR2(100);
            v_cpf_pac_id VARCHAR2(20);
            v_same_cd NUMBER;

            BEGIN

            app_agd.BUSCAR_PAC_BOT(
                P_ORIGEM        => p_origem,
                P_PATIENT_ID    => p_patient_id,
                P_PATIENT_PHONE => p_patient_phone,
                P_ERRO          => p_erro,
                P_ERRO_CD       => p_erro_cd,
                P_ERRO_MT       => p_erro_mt,
                P_RECORDSET     => p_recordset
            );
                DBMS_OUTPUT.PUT_LINE('----- INICIO DOS REGISTROS -----');
                DBMS_OUTPUT.PUT_LINE(RPAD('-', 80, '-'));
            LOOP
                FETCH p_recordset INTO v_cd_app, v_nome, v_dt_nasc, v_sexo, v_telefone, v_email, v_cpf_pac_id, v_same_cd;
                EXIT WHEN p_recordset%NOTFOUND;
                
                DBMS_OUTPUT.PUT_LINE('CD_APP: ' || v_cd_app);
                DBMS_OUTPUT.PUT_LINE('Nome: ' || v_nome);
                DBMS_OUTPUT.PUT_LINE('Data de Nascimento: ' || TO_CHAR(v_dt_nasc, 'DD/MM/YYYY'));
                DBMS_OUTPUT.PUT_LINE('Sexo: ' || v_sexo);
                DBMS_OUTPUT.PUT_LINE('Telefone: ' || v_telefone);
                DBMS_OUTPUT.PUT_LINE('Email: ' || v_email);
                DBMS_OUTPUT.PUT_LINE('CPF/PAC ID: ' || v_cpf_pac_id);
                DBMS_OUTPUT.PUT_LINE('SAME CD: ' || v_same_cd);
                DBMS_OUTPUT.PUT_LINE(RPAD('-', 80, '-'));
            END LOOP;
            DBMS_OUTPUT.PUT_LINE('----- FIM DOS REGISTROS -----');
            CLOSE p_recordset;

            IF p_erro THEN
                DBMS_OUTPUT.PUT_LINE('Erro: ' || TO_CHAR(p_erro_cd) || ' - ' || p_erro_mt);
            END IF;
            END;
            /
            """

            try:
                client = get_ssh_client(config('HOSTNAME'), config('SSH_PORT', cast=int), config('USERNAME_ORACLE'), config('PASSWORD'))
                stdin, stdout, stderr = client.exec_command(f"""
                export LD_LIBRARY_PATH={config('SQLPLUS_PATH')}:$LD_LIBRARY_PATH
                export PATH={config('SQLPLUS_PATH')}:$PATH
                echo "{plsql_block}" | sqlplus -S {config('CONNECTION_STRING')}
                """)
                errors = stderr.read().decode('utf-8')
                if errors:
                    return {"error": errors}, None

                output = stdout.read().decode('utf-8').strip()
            

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
                return {"error": str(e)}, None # Erro no SSH
            finally:
                client.close()

class CadastrarNovoPaciente(APIView):
    parser_classes = [JSONParser]
    def post(self, request, *args, **kwargs):
        data = request.data
        logger.info("Dados recebidos para cadastro:", data)
        data_nascimento_formatada = datetime.strptime(data.get('Data de Nascimento'), '%d/%m/%Y').strftime('%Y-%m-%d')
        try:
            client = get_ssh_client(config('HOSTNAME'), config('SSH_PORT', cast=int), config('USERNAME_ORACLE'), config('PASSWORD'))
            plsql_block = f"""
            SET SERVEROUTPUT ON SIZE UNLIMITED;
            DECLARE
                p_erro BOOLEAN := FALSE;
                p_erro_cd NUMBER := NULL;
                p_erro_mt VARCHAR2(4000) := NULL;
                p_cd_bot NUMBER := NULL;
                p_origem VARCHAR2(100) := 'C';
                p_patient_id NUMBER := {data.get('CPF')};
                p_patient_age NUMBER := {data.get('Idade')};
                p_patient_name VARCHAR2(100) := '{data.get('Nome')} {data.get('Sobrenome')}';
                p_patient_gender VARCHAR2(1) := '{data.get('Sexo')}';
                p_patient_date_of_birth DATE := TO_DATE('{data_nascimento_formatada}', 'YYYY-MM-DD');
                p_patient_phone VARCHAR2(100) := '{data.get('telefone')}';
                p_patient_email VARCHAR2(100) := '{data.get('Email')}';
                p_patient_cpf VARCHAR2(100) := '{data.get('CPF')}';
            BEGIN
                app_agd.GERA_CD_PAC_BOT(
                    P_ERRO                 => p_erro,
                    P_ERRO_CD              => p_erro_cd,
                    P_ERRO_MT              => p_erro_mt,
                    P_CD_BOT               => p_cd_bot,
                    P_ORIGEM               => p_origem,
                    P_PATIENT_ID           => p_patient_id,
                    P_PATIENT_AGE          => p_patient_age,
                    P_PATIENT_NAME         => p_patient_name,
                    P_PATIENT_GENDER       => p_patient_gender,
                    P_PATIENT_DATE_OF_BIRTH=> p_patient_date_of_birth,
                    P_PATIENT_PHONE        => p_patient_phone,
                    P_PATIENT_EMAIL        => p_patient_email,
                    P_PATIENT_CPF          => p_patient_cpf
                );
            
                IF p_erro THEN
                    DBMS_OUTPUT.PUT_LINE('Erro: ' || TO_CHAR(p_erro_cd) || ' - ' || p_erro_mt);
                ELSE
                    COMMIT;
                    DBMS_OUTPUT.PUT_LINE('Cadastro de paciente realizado com sucesso. Código BOT gerado: ' || p_cd_bot);
                END IF;
            EXCEPTION
                WHEN OTHERS THEN
                    DBMS_OUTPUT.PUT_LINE('Exceção capturada: ' || SQLERRM);
                    ROLLBACK;
                    RAISE;
            END;
            /
            """

            # Execute the command
            stdin, stdout, stderr = client.exec_command(f"""
            export LD_LIBRARY_PATH={config('SQLPLUS_PATH')}:$LD_LIBRARY_PATH
            export PATH={config('SQLPLUS_PATH')}:$PATH
            echo "{plsql_block}" | sqlplus -S {config('CONNECTION_STRING')}
            """)

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
                    return Response({"message": "Cadastro de paciente realizado com sucesso.", "codigo": codigo_bot}, status=status.HTTP_200_OK)
                else:
                    return Response({"message": "Cadastro de paciente realizado com sucesso.", "output": output.replace('\n', ' ')}, status=status.HTTP_200_OK)
            else:
                return Response({"message": "Resposta não reconhecida.", "output": output.replace('\n', ' ')}, status=status.HTTP_200_OK)
        except paramiko.SSHException as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        finally:
            client.close()

class BuscarDataDisponivel(APIView):
    # app_agd.p_get_date_crm
    """
    COnfirma disponibilidade do médico na data informada
    Endpoint para buscar datas disponíveis para procedimentos médicos em unidades específicas.

    Parâmetros do POST:

    - Unidade: Nome da unidade hospitalar (obrigatório). Deve ser uma das seguintes opções:
        - 1: Belem 
        - 17: Santana
        - 19: Aricanduva
        - 20: Interlagos
        - 21: Tucuruvi
        - 22: Eldorado
        - 23: S.BERNARDO
        - 24: Itaquera
        - 25: W.Plaza
        - 26: Guarulhos
        - 28: Osasco
        - 31: Ibirapuera

    - procedimento: Tipo de procedimento médico (obrigatório). Opções disponíveis:
        - 1: OFTALMOLOGIA
        - 2: OTORRINOLARINGOLOGIA
    - data_consulta`: Data para a qual a disponibilidade deve ser verificada (opcional). Se não for passada usa data atual como padrão

     Funcionalidade:
    Este endpoint interage com o sistema hospitalar para buscar disponibilidade de agendas baseadas na unidade e tipo de procedimento especificado. Retorna uma lista de datas e informações relacionadas, facilitando o agendamento de procedimentos pelos usuários.

     Exemplo de Uso:
    Para usar este endpoint, envie uma requisição POST com JSON contendo os campos 'unidade' e 'procedimento' especificados.

     Requisição de exemplo:
    json
    {
        "unidade": "Belem",
        "procedimento": "OFTALMOLOGIA"
        "data_consulta": "20/05/24"
    }
    ```

     Resposta:
    A resposta será uma lista de objetos, cada um representando uma data disponível e informações relacionadas, como código da unidade, descrição do procedimento, etc.
    """
    parser_classes = [JSONParser]
    def post(self, request, *args, **kwargs):
        data = request.data
        unidade_mapping = {
            'BELEM': {'codigo': 1, 'nome': 'BELEM'},
            'SANTANA': {'codigo': 17, 'nome': 'SANTANA'},
            'ARICANDUVA': {'codigo': 19, 'nome': 'ARICANDUVA'},
            'INTERLAGOS': {'codigo': 20, 'nome': 'INTERLAGOS'},
            'TUCURUVI': {'codigo': 21, 'nome': 'TUCURUVI'},
            'ELDORADO': {'codigo': 22, 'nome': 'ELDORADO'},
            'S.BERNARDO': {'codigo': 23, 'nome': 'S.BERNARDO'},
            'ITAQUERA': {'codigo': 24, 'nome': 'ITAQUERA'},
            'W.PLAZA': {'codigo': 25, 'nome': 'W.PLAZA'},
            'GUARULHOS': {'codigo': 26, 'nome': 'GUARULHOS'},
            'OSASCO': {'codigo': 28, 'nome': 'OSASCO'},
            'IBIRAPUERA': {'codigo': 31, 'nome': 'IBIRAPUERA'}
        }

        especialidade_mapping = {
            'OFTALMOLOGIA': {'codigo': 1, 'descricao': 'Oftalmologia'},
            'OTORRINOLARINGOLOGIA': {'codigo': 2, 'descricao': 'Otorrinolaringologia'}
        }

        unidade = data.get('unidade', '').upper()
        especialidade = data.get('especialidade', '').upper()
        data_consulta = data.get('data_consulta', datetime.now().strftime('%d/%m/%Y'))

        if unidade not in unidade_mapping or especialidade not in especialidade_mapping:
            return Response({"error": "Unidade ou especialidade inválido."}, status=status.HTTP_400_BAD_REQUEST)


        unidade_codigo = unidade_mapping[unidade]['codigo']
        especialidade_codigo = especialidade_mapping[especialidade]['codigo']


        try:
            data_consulta_obj = datetime.strptime(data_consulta, '%d/%m/%Y')
            if data_consulta_obj.date() < datetime.now().date():
                return Response({"error": "Data de consulta inválida ou anterior à data atual."}, status=status.HTTP_400_BAD_REQUEST)
            data_formatada = data_consulta_obj.strftime('%Y-%m-%d')
        except ValueError:
            return Response({"error": "Formato de data inválido. Use 'DD/MM/YYYY'."}, status=status.HTTP_400_BAD_REQUEST)
        

        plsql_block = f"""
        SET SERVEROUTPUT ON SIZE UNLIMITED;
        
        DECLARE
            p_erro BOOLEAN := FALSE;
            p_erro_cd NUMBER;
            p_erro_mt VARCHAR2(4000);
            p_recordset SYS_REFCURSOR;
            p_origem VARCHAR2(100) := 'C';
            p_vunid_cd NUMBER := {unidade_codigo};
            p_vgpro_cd NUMBER := 1;
            p_vprre_cd NUMBER := {especialidade_codigo};
            p_vsues_cd NUMBER := NULL;
            p_vdt DATE := TO_DATE('{data_formatada}', 'YYYY-MM-DD');
            p_vdt_fim DATE := NULL;
            p_vcocl_cd NUMBER := NULL;

            v_vunid_cd NUMBER;
            v_vunid_ds VARCHAR2(100);
            v_vcocl_cd NUMBER;
            v_vcocl_nm VARCHAR2(100);
            v_vgpro_cd NUMBER;
            v_vgpro_ds VARCHAR2(100);
            v_vagma_cd NUMBER;
            v_vagma_ds VARCHAR2(100);
            v_vprre_cd NUMBER;
            v_vprre_ds VARCHAR2(100);
            v_vsues_cd NUMBER;
            v_vsues_ds VARCHAR2(100);
            v_vagen_dt DATE;
            v_vperc NUMBER;
            v_vidade_min NUMBER;
            v_vidade_max NUMBER;
            v_vfl_nariz VARCHAR2(1);
            v_vfl_garganta VARCHAR2(1);
            v_vfl_ouvido VARCHAR2(1);

        BEGIN
            app_agd.p_get_date_crm(
                p_origem     => p_origem,
                p_vunid_cd   => p_vunid_cd,
                p_vgpro_cd   => p_vgpro_cd,
                p_vprre_cd   => p_vprre_cd,
                p_vsues_cd   => p_vsues_cd,
                p_vdt        => p_vdt,
                p_vdt_fim    => p_vdt_fim,
                p_vcocl_cd   => p_vcocl_cd,
                p_erro       => p_erro,
                p_erro_cd    => p_erro_cd,
                p_erro_mt    => p_erro_mt,
                p_recordset  => p_recordset
            );

            DBMS_OUTPUT.PUT_LINE('----- INÍCIO DOS REGISTROS -----');
            DBMS_OUTPUT.PUT_LINE(RPAD('-', 80, '-'));

            IF p_erro THEN
                DBMS_OUTPUT.PUT_LINE('Erro encontrado: ' || p_erro_cd || ' - ' || p_erro_mt);
            ELSE
                DBMS_OUTPUT.PUT_LINE('Processando resultados...');
                LOOP
                    FETCH p_recordset INTO v_vunid_cd, v_vunid_ds, v_vcocl_cd, v_vcocl_nm, v_vgpro_cd, v_vgpro_ds, v_vagma_cd, v_vagma_ds, v_vprre_cd, v_vprre_ds, v_vsues_cd, v_vsues_ds, v_vagen_dt, v_vperc, v_vidade_min, v_vidade_max, v_vfl_nariz, v_vfl_garganta, v_vfl_ouvido;
                    EXIT WHEN p_recordset%NOTFOUND;
            
                    DBMS_OUTPUT.PUT_LINE('VUNID_CD: ' || v_vunid_cd);
                    DBMS_OUTPUT.PUT_LINE('VUNID_DS: ' || v_vunid_ds);
                    DBMS_OUTPUT.PUT_LINE('VCOCL_CD: ' || v_vcocl_cd);
                    DBMS_OUTPUT.PUT_LINE('VCOCL_NM: ' || v_vcocl_nm);
                    DBMS_OUTPUT.PUT_LINE('VGPRO_CD: ' || v_vgpro_cd);
                    DBMS_OUTPUT.PUT_LINE('VGPRO_DS: ' || v_vgpro_ds);
                    DBMS_OUTPUT.PUT_LINE('VAGMA_CD: ' || v_vagma_cd);
                    DBMS_OUTPUT.PUT_LINE('VAGMA_DS: ' || v_vagma_ds);
                    DBMS_OUTPUT.PUT_LINE('VPRRE_CD: ' || v_vprre_cd);
                    DBMS_OUTPUT.PUT_LINE('VPRRE_DS: ' || v_vprre_ds);
                    DBMS_OUTPUT.PUT_LINE('VSUES_CD: ' || v_vsues_cd);
                    DBMS_OUTPUT.PUT_LINE('VSUES_DS: ' || v_vsues_ds);
                    DBMS_OUTPUT.PUT_LINE('VAGEN_DT: ' || TO_CHAR(v_vagen_dt, 'DD/MM/YYYY'));
                    DBMS_OUTPUT.PUT_LINE('VPERC: ' || v_vperc);
                    DBMS_OUTPUT.PUT_LINE('VIDADE_MIN: ' || v_vidade_min);
                    DBMS_OUTPUT.PUT_LINE('VIDADE_MAX: ' || v_vidade_max);
                    DBMS_OUTPUT.PUT_LINE('VFL_NARIZ: ' || v_vfl_nariz);
                    DBMS_OUTPUT.PUT_LINE('VFL_GARGANTA: ' || v_vfl_garganta);
                    DBMS_OUTPUT.PUT_LINE('VFL_OUVIDO: ' || v_vfl_ouvido);
                    DBMS_OUTPUT.PUT_LINE(RPAD('-', 80, '-'));
                END LOOP;
                CLOSE p_recordset;
            END IF;
        EXCEPTION
            WHEN OTHERS THEN
                DBMS_OUTPUT.PUT_LINE('Exceção SQL capturada: ' || SQLCODE || ' - ' || SQLERRM);
        END;
        /
        """
        try:
            client = get_ssh_client(config('HOSTNAME'), config('SSH_PORT', cast=int), config('USERNAME_ORACLE'), config('PASSWORD'))
            stdin, stdout, stderr = client.exec_command(f"""
            export LD_LIBRARY_PATH={config('SQLPLUS_PATH')}:$LD_LIBRARY_PATH
            export PATH={config('SQLPLUS_PATH')}:$PATH
            echo "{plsql_block}" | sqlplus -S {config('CONNECTION_STRING')}
            """)
            
            errors = stderr.read().decode('utf-8')
            if errors:
                return {"error": errors}, None
            
            output = stdout.read().decode('utf-8').strip()
            
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

            # Agrupar resultados por médico
            grouped_results = {}
            for result in results:
                medico_id = result.get('VCOCL_CD', 'Não especificado')
                if medico_id not in grouped_results:
                    grouped_results[medico_id] = {
                        "Unidade": unidade_mapping.get(unidade, {'nome': 'Desconhecido'})['nome'],
                        "ID Médico": medico_id,
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
    """ Endpoint para buscar horários de consultas disponíveis.

    Este endpoint espera receber uma requisição POST com os seguintes parâmetros:
    - id_medico: Opcional. CRM do médico. Se não for fornecido, a busca retornará horários disponíveis de todos os médicos para a especialidade e sub-especialidade especificadas.
    - unidade: Obrigatório. Unidade hospitalar onde a consulta será realizada.
    - especialidade: Obrigatório. Especialidade médica da consulta.
    - sub_especialidade: Obrigatório. Sub-especialidade dentro da especialidade médica.
    - data_consulta: Obrigatório. Data desejada para a consulta no formato 'DD/MM/YYYY'.

    A resposta será um JSON contendo os horários disponíveis. Se o 'id_medico' não for fornecido,
    a busca incluirá todos os médicos qualificados na unidade e especialidade solicitadas.
    """

    # app_agd.p_bc_get_date
    parser_classes = [JSONParser]

    def query_database(self, custom_query=None, column_names=None):
        return super().query_database(custom_query=custom_query, column_names=column_names)

    def post(self, request, *args, **kwargs):
        data = request.data

        unidade_mapping = {
            'BELEM': {'codigo': 1, 'nome': 'BELEM'},
            'SANTANA': {'codigo': 17, 'nome': 'SANTANA'},
            'ARICANDUVA': {'codigo': 19, 'nome': 'ARICANDUVA'},
            'INTERLAGOS': {'codigo': 20, 'nome': 'INTERLAGOS'},
            'TUCURUVI': {'codigo': 21, 'nome': 'TUCURUVI'},
            'ELDORADO': {'codigo': 22, 'nome': 'ELDORADO'},
            'S.BERNARDO': {'codigo': 23, 'nome': 'S.BERNARDO'},
            'ITAQUERA': {'codigo': 24, 'nome': 'ITAQUERA'},
            'W.PLAZA': {'codigo': 25, 'nome': 'W.PLAZA'},
            'GUARULHOS': {'codigo': 26, 'nome': 'GUARULHOS'},
            'OSASCO': {'codigo': 28, 'nome': 'OSASCO'},
            'IBIRAPUERA': {'codigo': 31, 'nome': 'IBIRAPUERA'}
        }

        especialidade_mapping = {
            'OFTALMOLOGIA': {'codigo': 1, 'descricao': 'Oftalmologia'},
            'OTORRINOLARINGOLOGIA': {'codigo': 2, 'descricao': 'Otorrinolaringologia'}
        }


        id_medico = data.get('id_medico', 'NULL')
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


        if unidade not in unidade_mapping or especialidade not in especialidade_mapping:
            return Response({"error": "Unidade ou especialidade inválido."}, status=status.HTTP_400_BAD_REQUEST)

        unidade_codigo = unidade_mapping[unidade]['codigo']
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
        
        if id_medico:
            id_medico_clause = f"p_vcocd_cd NUMBER := {id_medico}"
        else:
            id_medico_clause = "p_vcocd_cd NUMBER := NULL"
        # Estabelece conexão SSH e executa o bloco PL/SQL
        try:
            
            plsql_block = f"""
            SET SERVEROUTPUT ON SIZE UNLIMITED;

            DECLARE
                p_erro BOOLEAN := FALSE;
                p_erro_cd NUMBER;
                p_erro_mt VARCHAR2(4000);
                p_recordset SYS_REFCURSOR;
                {id_medico_clause};
                p_vunid_cd NUMBER := {unidade_codigo}; 
                p_vgpro_cd NUMBER := {vprre_codigo};
                p_vprre_cd NUMBER := {especialidade_codigo};
                p_vsues_cd NUMBER := {subespecialidade_cd};
                p_vdt DATE := TO_DATE('{data_formatada}', 'YYYY-MM-DD');
                p_vdt_fim DATE := NULL; 
                v_vunid_cd NUMBER;
                v_vunid_ds VARCHAR2(100);
                v_vcocl_cd NUMBER;
                v_vcocl_nm VARCHAR2(100);
                v_vgpro_cd NUMBER;
                v_vgpro_ds VARCHAR2(100);
                v_vagma_cd NUMBER;
                v_vagma_ds VARCHAR2(100);
                v_vprre_cd NUMBER;
                v_vprre_ds VARCHAR2(100);
                v_vsues_cd NUMBER;
                v_vsues_ds VARCHAR2(100);
                v_agen_dt DATE;
                v_vagho_hh NUMBER;
                v_vagho_mi NUMBER;
                v_perc NUMBER;
                v_seq NUMBER;
                v_idade_min NUMBER;
                v_idade_max NUMBER;
                v_fl_nariz VARCHAR2(1);
                v_fl_garganta VARCHAR2(1);
                v_fl_ouvido VARCHAR2(1);
            BEGIN
                app_agd.p_bc_get_date(
                P_VCOCL_CD   => p_vcocd_cd,
                P_ERRO       => p_erro,
                P_ERRO_CD    => p_erro_cd,
                P_ERRO_MT    => p_erro_mt,
                P_RECORDSET  => p_recordset,
                P_ORIGEM     => 'C',
                P_VUNID_CD   => p_vunid_cd,
                P_VGPRO_CD   => p_vgpro_cd,
                P_VPRRE_CD   => p_vprre_cd,
                P_VSUES_CD   => p_vsues_cd,
                P_VDT        => p_vdt,
                P_VDT_FIM    => p_vdt_fim
            );
                DBMS_OUTPUT.PUT_LINE('----- INICIO DOS REGISTROS -----');
                DBMS_OUTPUT.PUT_LINE(RPAD('-', 80, '-'));
              LOOP
                FETCH p_recordset INTO v_vunid_cd, v_vunid_ds, v_vcocl_cd, v_vcocl_nm, v_vgpro_cd, v_vgpro_ds,
                                    v_vagma_cd, v_vagma_ds, v_vprre_cd, v_vprre_ds, v_vsues_cd, v_vsues_ds,
                                    v_agen_dt, v_vagho_hh, v_vagho_mi, v_perc, v_seq, v_idade_min, v_idade_max,
                                    v_fl_nariz, v_fl_garganta, v_fl_ouvido;
                EXIT WHEN p_recordset%NOTFOUND;
                
                DBMS_OUTPUT.PUT_LINE('Unidade: ' || v_vunid_ds);
                DBMS_OUTPUT.PUT_LINE('Unidade CD: ' || v_vunid_cd || ' DS: ' || v_vunid_ds);
                DBMS_OUTPUT.PUT_LINE('Codigo Local CD: ' || v_vcocl_cd || ' NM: ' || v_vcocl_nm);
                DBMS_OUTPUT.PUT_LINE('Grupo Produto CD: ' || v_vgpro_cd || ' DS: ' || v_vgpro_ds);
                DBMS_OUTPUT.PUT_LINE('Maquina CD: ' || v_vagma_cd || ' DS: ' || v_vagma_ds);
                DBMS_OUTPUT.PUT_LINE('Preco CD: ' || v_vprre_cd || ' DS: ' || v_vprre_ds);
                DBMS_OUTPUT.PUT_LINE('SUS CD: ' || v_vsues_cd || ' DS: ' || v_vsues_ds);
                DBMS_OUTPUT.PUT_LINE('Data Agendamento: ' || TO_CHAR(v_agen_dt, 'DD-MON-YYYY'));
                DBMS_OUTPUT.PUT_LINE('Hora HH: ' || LPAD(v_vagho_hh, 2, '0') || ':' || LPAD(v_vagho_mi, 2, '0'));
                DBMS_OUTPUT.PUT_LINE('Percentual: ' || v_perc);
                DBMS_OUTPUT.PUT_LINE('Sequencia: ' || v_seq);
                DBMS_OUTPUT.PUT_LINE('Idade Minima: ' || v_idade_min || ' Maxima: ' || v_idade_max);
                DBMS_OUTPUT.PUT_LINE('Nariz: ' || v_fl_nariz);
                DBMS_OUTPUT.PUT_LINE('Garganta: ' || v_fl_garganta);
                DBMS_OUTPUT.PUT_LINE('Ouvido: ' || v_fl_ouvido);
                DBMS_OUTPUT.PUT_LINE(RPAD('-', 80, '-'));
            END LOOP;
            DBMS_OUTPUT.PUT_LINE('----- FIM DOS REGISTROS -----');

            CLOSE p_recordset;

            IF p_erro THEN
                DBMS_OUTPUT.PUT_LINE('Erro: ' || TO_CHAR(p_erro_cd) || ' - ' || p_erro_mt);
            END IF;
            END;
            /
            """
            client = get_ssh_client(config('HOSTNAME'), config('SSH_PORT', cast=int), config('USERNAME_ORACLE'), config('PASSWORD'))
            stdin, stdout, stderr = client.exec_command(f"""
            export LD_LIBRARY_PATH={config('SQLPLUS_PATH')}:$LD_LIBRARY_PATH
            export PATH={config('SQLPLUS_PATH')}:$PATH
            echo "{plsql_block}" | sqlplus -S {config('CONNECTION_STRING')}
            """)

            logger.info(plsql_block)
            
            output = stdout.read().decode().strip()
            errors = stderr.read().decode().strip()
            if errors:
                return Response({"error": errors}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            # Processa a saída para extrair informações
            
            results = self.parse_output(output)
            if not results:
                return Response({"message": "Nenhum horário disponível para os critérios selecionados."}, status=status.HTTP_200_OK)

            return Response({"data": results}, status=status.HTTP_200_OK)
        except paramiko.SSHException as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        finally:
            client.close()

    def parse_output(self, output):
        results = {}
        nome_medico = None  # Variável para manter o nome do médico atual
        data_found = False  # Flag para verificar se alguma data válida foi encontrada

        lines = output.split('\n')
        for line in lines:
            if 'Unidade' in line and 'DS:' in line:
                unidade = line.split('DS: ')[1].strip()
                data_found = True  # Ajusta a flag quando um registro válido começa
            elif 'Codigo Local CD' in line and 'NM:' in line:
                nome_medico = line.split('NM: ')[1].strip()
                if nome_medico not in results:
                    results[nome_medico] = {
                        "Unidade": unidade,
                        "Nome Médico": nome_medico,
                        "Horários": [],
                        "Data Agendamento": None
                    }
            elif 'Data Agendamento' in line:
                data_agendamento = line.split(': ')[1].strip()
                if nome_medico:
                    results[nome_medico]["Data Agendamento"] = data_agendamento
            elif 'Hora HH' in line:
                hora = line.split(': ')[1].strip()
                if nome_medico:
                    results[nome_medico]["Horários"].append(hora)

        if not data_found:  # Se não encontrou nenhum registro válido
            return {"message": "Nenhum horário disponível para os critérios selecionados."}
        else:
            return {"data": list(results.values())}


class RealizarAgendamento(BaseView):
    parser_classes = [JSONParser]

    def query_database(self, custom_query=None, column_names=None):
        return super().query_database(custom_query=custom_query, column_names=column_names)


    def post(self, request, *args, **kwargs):
        data = request.data

        unidade_mapping = {
            'BELEM': {'codigo': 1, 'nome': 'BELEM'},
            'SANTANA': {'codigo': 17, 'nome': 'SANTANA'},
            'ARICANDUVA': {'codigo': 19, 'nome': 'ARICANDUVA'},
            'INTERLAGOS': {'codigo': 20, 'nome': 'INTERLAGOS'},
            'TUCURUVI': {'codigo': 21, 'nome': 'TUCURUVI'},
            'ELDORADO': {'codigo': 22, 'nome': 'ELDORADO'},
            'S.BERNARDO': {'codigo': 23, 'nome': 'S.BERNARDO'},
            'ITAQUERA': {'codigo': 24, 'nome': 'ITAQUERA'},
            'W.PLAZA': {'codigo': 25, 'nome': 'W.PLAZA'},
            'GUARULHOS': {'codigo': 26, 'nome': 'GUARULHOS'},
            'OSASCO': {'codigo': 28, 'nome': 'OSASCO'},
            'IBIRAPUERA': {'codigo': 31, 'nome': 'IBIRAPUERA'}
        }

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
        idade  = data.get('idade_paciente', 'Não especificado')
        nome_paciente = data.get('nome_paciente', 'Não especificado')
        genero_paciente = data.get('genero', 'Não especificado')
        data_nascimento = data.get('data_nascimento', 'Não especificado')
        telefone_paciente = data.get('telefone', 'Não especificado')
        email = data.get('email', 'Não especificado')

         # Converting data_consulta from string to datetime object
        try:
            data_consulta_obj = datetime.strptime(data_consulta, '%d/%m/%Y')
            data_formatada = data_consulta_obj.strftime('%Y-%m-%d')
        except ValueError:
            return Response({"error": "Formato de data inválido. Use 'DD/MM/YYYY'."}, status=status.HTTP_400_BAD_REQUEST)

        # Converter data_nascimento de string para objeto datetime
        try:
            if data_nascimento != 'Não especificado':
                data_nascimento_obj = datetime.strptime(data_nascimento, '%d/%m/%Y')
                data_nascimento_formatada = data_nascimento_obj.strftime('%Y-%m-%d')
            else:
                data_nascimento_formatada = 'Não especificado'
        except ValueError:
            return Response({"error": "Formato de data de nascimento inválido. Use 'DD/MM/YYYY'."}, status=status.HTTP_400_BAD_REQUEST)


        if unidade not in unidade_mapping or especialidade not in especialidade_mapping:
            return Response({"error": "Unidade ou especialidade inválido."}, status=status.HTTP_400_BAD_REQUEST)

        unidade_codigo = unidade_mapping[unidade]['codigo']
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

        # Obtem código do convenio
        convenio_query = f"""
        SELECT VCONV_CD FROM V_APP_CONVENIO WHERE UPPER(VCONV_DS) = UPPER('{descricao_convenio}');
        """
        response = self.query_database(custom_query=convenio_query, column_names=["VCONV_CD"])

        # Verificar se a resposta foi bem-sucedida
        if response.status_code != 200:
            return Response({"error": "Erro ao buscar convenio."}, status=response.status_code)

        convenio_data = response.data.get('data', [])

        if not convenio_data:
            return Response({"error": f"Convenio {descricao_convenio} não encontrado"}, status=400)
        
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
            return Response({"error": "Erro ao buscar plano."}, status=response.status_code)

        plano_data = response.data.get('data', [])
        
        if not plano_data:
            return Response({"error": f"Plano {descricao_plano} não encontrado"}, status=400)
        
        plano_cd, subplano_cd = plano_data[0]['VPLAN_CD'], plano_data[0]['VSUP2_CD']
        logger.info(f'Codigo do plano {descricao_plano}: {plano_cd}')
        logger.info(f'Codigo do subplano: {subplano_cd}')

        
        
        try:            
            # Montagem do comando PL/SQL a ser executado
            plsql_command = f"""
            SET SERVEROUTPUT ON SIZE UNLIMITED;

            DECLARE
                p_erro BOOLEAN := FALSE;
                p_erro_cd NUMBER;
                p_erro_mt VARCHAR2(4000);
                p_cd_agend NUMBER;
                p_obs_agend VARCHAR2(4000);
                p_aaso_ano NUMBER := NULL;
                p_aaso_cd NUMBER := NULL;
                p_origem VARCHAR2(100) := 'C';
                p_vunid_cd NUMBER := {unidade_codigo};
                p_vgpro_cd NUMBER := {vconsulta};
                p_vprre_cd NUMBER := {especialidade_codigo};
                p_vsues_cd NUMBER := {subespecialidade_cd};
                p_vconv_cd NUMBER := {convenio_cd};
                p_vpla2_cd NUMBER := {plano_cd};
                p_vsup2_cd VARCHAR2(100) := '{subplano_cd}';
                p_vdt DATE := TO_DATE('{data_formatada}', 'YYYY-MM-DD');
                p_vhh NUMBER := {hora_agenda};
                p_vmi NUMBER := {minuto_agenda};
                p_vcocl_cd NUMBER := {crm_medico};
                p_patient_id NUMBER := {cpf};
                p_patient_age NUMBER := NULL;
                p_patient_name VARCHAR2(100) := NULL;
                p_patient_gender VARCHAR2(100) := NULL;
                p_patient_dob DATE := NULL;
                p_patient_phone VARCHAR2(100) := NULL;
                p_patient_email VARCHAR2(100) := NULL;
                p_patient_cpf VARCHAR2(100) := NULL;

            BEGIN
                app_agd.P_APP_AGENDAR(
                    p_erro, p_erro_cd, p_erro_mt, p_cd_agend, p_obs_agend, p_aaso_ano, p_aaso_cd, p_origem,
                    p_vunid_cd, p_vgpro_cd, p_vprre_cd, p_vsues_cd, p_vconv_cd, p_vpla2_cd, p_vsup2_cd,
                    p_vdt, p_vhh, p_vmi, p_vcocl_cd, p_patient_id, p_patient_age, p_patient_name, p_patient_gender,
                    p_patient_dob, p_patient_phone, p_patient_email, p_patient_cpf
                );

                IF p_erro THEN
                    DBMS_OUTPUT.PUT_LINE('Erro: ' || p_erro_mt || ' Código de Erro: ' || TO_CHAR(p_erro_cd) || ' Código de Agendamento: ' || TO_CHAR(p_cd_agend));
                ELSE
                    DBMS_OUTPUT.PUT_LINE('Agendamento realizado com sucesso. Código: ' || TO_CHAR(p_cd_agend) || ' Observações: ' || p_obs_agend);
                END IF;
            END;
            /
            """
            client = get_ssh_client(config('HOSTNAME'), config('SSH_PORT', cast=int), config('USERNAME_ORACLE'), config('PASSWORD'))
            stdin, stdout, stderr = client.exec_command(f"""
            export LD_LIBRARY_PATH={config('SQLPLUS_PATH')}:$LD_LIBRARY_PATH
            export PATH={config('SQLPLUS_PATH')}:$PATH
            echo "{plsql_command}" | sqlplus -S {config('CONNECTION_STRING')}
            """)

            logger.info(plsql_command)

            output = stdout.read().decode().strip()
            errors = stderr.read().decode().strip()

            if errors:
                return Response({"error": errors}, status=status.HTTP_400_BAD_REQUEST)

            return Response({"message": output}, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        finally:
            if client:
                client.close()


class CadastrarNovoConveio(APIView):
    # app_agd.GERA_PAC_BOT_CNV
    pass


class SelecionarProfissional(APIView):
    # app_agd.p_bc_get_doctors
    pass

