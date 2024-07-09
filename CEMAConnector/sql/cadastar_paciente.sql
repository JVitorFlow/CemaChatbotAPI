SET SERVEROUTPUT ON SIZE UNLIMITED;
DECLARE
    p_erro BOOLEAN := FALSE;
    p_erro_cd NUMBER := NULL;
    p_erro_mt VARCHAR2(4000) := NULL;
    p_cd_bot NUMBER := NULL;
    p_origem VARCHAR2(100) := 'C';
    p_patient_id NUMBER := {cpf};
    p_patient_age NUMBER := {idade};
    p_patient_name VARCHAR2(100) := '{nome} {sobrenome}';
    p_patient_gender VARCHAR2(1) := '{sexo}';
    p_patient_date_of_birth DATE := TO_DATE('{data_nascimento_formatada}', 'YYYY-MM-DD');
    p_patient_phone VARCHAR2(100) := '{telefone}';
    p_patient_email VARCHAR2(100) := '{email';
    p_patient_cpf VARCHAR2(100) := '{cpf}';
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