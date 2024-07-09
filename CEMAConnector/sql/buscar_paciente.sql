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