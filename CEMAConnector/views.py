from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import JSONParser
from decouple import config
from .utils.ssh_utils import get_ssh_client
import re
import paramiko

class DynamicDataQuery(APIView):
    parser_classes = [JSONParser]

    VIEW_COLUMN_MAPPING = {
        'v_app_subesp': ['VGPRO_CD', 'VGPRO_DS', 'VPRRE_CD', 'VPRRE_DS', 'VSUES_CD', 'VSUES_DS', 'VVOX', 'VTODOS'],
        'v_app_unid': ['VUNID_CD', 'VUNID_DS', 'VLOGRADOURO', 'VNR', 'VCOMPL', 'VBAIRRO', 'VCIDADE', 'VCEP', 'VUF', 'VDDD', 'VTEL', 'VRAMAL', 'VUNID_APRES', 'VUNID_LOCAL'],
        'V_APP_PROCED': ['VGPRO_CD', 'VGPRO_DS', 'VPRRE_CD', 'VPRRE_DS', 'VITCO_CD']
        
    }

    def post(self, request, format=None):
        hostname = config('HOSTNAME')
        ssh_port = config('SSH_PORT', cast=int)
        username = config('USERNAME_ORACLE')
        password = config('PASSWORD')
        sqlplus_path = config('SQLPLUS_PATH')
        connection_string = config('CONNECTION_STRING')

        table_name = request.data.get('table_name')
        filters = request.data.get('filters', {})

        column_names = self.VIEW_COLUMN_MAPPING.get(table_name)
        if not column_names:
            return Response({"error": f"Invalid or missing table name: {table_name}"}, status=status.HTTP_400_BAD_REQUEST)

        # Construir a cláusula WHERE dinamicamente
        column_names = self.VIEW_COLUMN_MAPPING[table_name]
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
            print("SSH Exception:", str(e))
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        