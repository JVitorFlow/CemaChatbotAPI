from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import JSONParser
from decouple import config
from .utils.ssh_utils import get_ssh_client
import re
import paramiko

class BaseView(APIView):
    parser_classes = [JSONParser]

    @staticmethod
    def query_database(table_name, column_names, request):
        hostname = config('HOSTNAME')
        ssh_port = config('SSH_PORT', cast=int)
        username = config('USERNAME_ORACLE')
        password = config('PASSWORD')
        sqlplus_path = config('SQLPLUS_PATH')
        connection_string = config('CONNECTION_STRING')

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
            data = [
                dict(zip(column_names, re.sub(r'\s+', ' ', line).strip().split('|')))
                for line in output.split('\n') if line and not line.startswith('-') and not line.isspace()
            ]
            return Response({"data": data}, status=status.HTTP_200_OK)
        except paramiko.SSHException as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class SubespView(BaseView):
    column_names = ['VGPRO_CD', 'VGPRO_DS', 'VPRRE_CD', 'VPRRE_DS', 'VSUES_CD', 'VSUES_DS', 'VVOX', 'VTODOS']
    table_name = 'v_app_subesp'

    def post(self, request, format=None):
        return self.query_database(self.table_name, self.column_names, request)

class UnidView(BaseView):
    column_names = ['VUNID_CD', 'VUNID_DS', 'VLOGRADOURO', 'VNR', 'VCOMPL', 'VBAIRRO', 'VCIDADE', 'VCEP', 'VUF', 'VDDD', 'VTEL', 'VRAMAL', 'VUNID_APRES', 'VUNID_LOCAL']
    table_name = 'v_app_unid'

    def post(self, request, format=None):
        return self.query_database(self.table_name, self.column_names, request)
class ProcedView(BaseView):
    parser_classes = [JSONParser]
    column_names = ['vGPRO_CD', 'VGPRO_DS','VPRRE_CD','VPRRE_DS','VITCO_CD']
    table_name = 'V_APP_PROCED'

    def post(self, request, format=None):
        return self.query_database(self.table_name, self.column_names, request)
    
class ConvPlanView(BaseView):
    parser_classes = [JSONParser]
    column_names = ['vCONV_CD', 'vCONV_DS', 'vPLAN_CD', 'vPLAN_DS', 'vSUP2_CD']
    table_name = 'V_APP_CONV_PLAN'

    def post(self, request, format=None):
        return self.query_database(self.table_name, self.column_names, request)

class BuscarConvenioView(BaseView):
    parser_classes = [JSONParser]

    def post(self, request, format=None):
        cpf = request.data.get('cpf')
        if not cpf:
            return Response({"error": "CPF não fornecido"}, status=status.HTTP_400_BAD_REQUEST)

        print("CPF recebido:", cpf)
        data = self.buscar_convenio(cpf)
        if 'error' in data:
            return Response({"error": data['error']}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        if not data.get('data'):
            return Response({"message": "Nenhum convenio encontrado associado a esse CPF."}, status=status.HTTP_404_NOT_FOUND)

        return Response({"data": data['data']}, status=status.HTTP_200_OK)

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
            DBMS_OUTPUT.PUT_LINE('Código Convênio: ' || v_cd_conv);
            DBMS_OUTPUT.PUT_LINE('Convênio: ' || v_convenio);
            DBMS_OUTPUT.PUT_LINE('Código Plano: ' || v_cd_plano);
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


class BuscarPacienteView(APIView):
    parser_classes = [JSONParser]

    def post(self, request, format=None):
        patient_phone = request.data.get('patient_phone')
        if not patient_phone:
            return Response({"error": "O número de telefone do paciente é obrigatório"}, status=status.HTTP_400_BAD_REQUEST)

        print("Paciente_phone recebido:", patient_phone)  # Debugging

        paciente, data_paciente = self.verificar_paciente(patient_phone)
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
                    return Response({"error": errors}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

                output = stdout.read().decode('utf-8').strip()
                print(output)

                # Processar a saída para criar objetos JSON
                data = {}
                for line in output.split('\n'):
                    if ':' in line:  # Verifica se a linha contém dados
                        key, value = line.split(':', 1)
                        data[key.strip()] = value.strip()

                if not data:  # Se nenhum dado foi adicionado ao dicionário
                    return Response({"message": "Nenhum registro encontrado para o número de telefone fornecido."}, status=status.HTTP_200_OK)

                return {}, data
            except paramiko.SSHException as e:
                return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            finally:
                client.close()

