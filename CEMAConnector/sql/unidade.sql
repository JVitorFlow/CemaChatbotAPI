SET LINESIZE 32767
SET PAGESIZE 50000
SET COLSEP '|'
SET TRIMSPOOL ON
SET WRAP OFF
SELECT VUNID_CD, VUNID_DS, VLOGRADOURO, VNR, VCOMPL, VBAIRRO, VCIDADE, VCEP, VUF, VDDD, VTEL, VRAMAL, VUNID_APRES, VUNID_LOCAL
FROM {table_name}
WHERE {where_clause}
{order_by};
EXIT;