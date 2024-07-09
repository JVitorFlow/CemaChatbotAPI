SET SERVEROUTPUT ON SIZE UNLIMITED;

DECLARE
p_erro BOOLEAN := FALSE;
p_erro_cd NUMBER;
p_erro_mt VARCHAR2(4000);
p_apbc_cd NUMBER;
p_origem VARCHAR2(2) := 'C';
p_tp_conv VARCHAR2(2) := 'C';
p_conv_cd NUMBER := {convenio_cd};
p_pla2_cd NUMBER := {plano_cd};
p_sup2_cd VARCHAR2(2) := '*';
p_patient_id NUMBER := {cpf};
BEGIN
app_agd.GERA_PAC_BOT_CNV(
    P_ERRO          => p_erro,
    P_ERRO_CD       => p_erro_cd,
    P_ERRO_MT       => p_erro_mt,
    P_APBC_CD       => p_apbc_cd,
    P_ORIGEM        => p_origem,
    P_TP_CONV       => p_tp_conv,
    P_CONV_CD       => p_conv_cd,
    P_PLA2_CD       => p_pla2_cd,
    P_SUP2_CD       => p_sup2_cd,
    P_PATIENT_ID    => p_patient_id
);
IF p_erro THEN
    DBMS_OUTPUT.PUT_LINE('Erro: ' || TO_CHAR(p_erro_cd) || ' - ' || p_erro_mt);
ELSE
    IF p_apbc_cd > 0 THEN
    DBMS_OUTPUT.PUT_LINE('Cadastro de convenio realizado com sucesso. Codigo gerado: ' || p_apbc_cd);
    ELSE
    DBMS_OUTPUT.PUT_LINE('Procedimento completado sem erros, mas não foi gerado um código válido.');
    END IF;
END IF;
END;
/