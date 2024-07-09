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