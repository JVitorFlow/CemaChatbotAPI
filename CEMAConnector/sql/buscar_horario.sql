SET SERVEROUTPUT ON SIZE UNLIMITED;

DECLARE
    p_erro BOOLEAN := FALSE;
    p_erro_cd NUMBER;
    p_erro_mt VARCHAR2(4000);
    p_recordset SYS_REFCURSOR;
    {crm_medico_clause};
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