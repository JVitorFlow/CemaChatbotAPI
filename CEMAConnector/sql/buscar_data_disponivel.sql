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
    p_vsues_cd NUMBER := {subespecialidade_cd};
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