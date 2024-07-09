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