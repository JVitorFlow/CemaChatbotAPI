SET SERVEROUTPUT ON SIZE UNLIMITED;
DECLARE
  p_erro BOOLEAN := FALSE;
  p_erro_cd NUMBER;
  p_erro_mt VARCHAR2(4000);
  p_origem VARCHAR2(2) := 'C';
  p_patient_id NUMBER := {patient_id};
  p_cd_agendam NUMBER := {cd_agendam};
BEGIN
  app_agd.P_APP_CANCELAR(
    P_ERRO          => p_erro,
    P_ERRO_CD       => p_erro_cd,
    P_ERRO_MT       => p_erro_mt,
    P_ORIGEM        => p_origem,
    P_PATIENT_ID    => p_patient_id,
    P_CD_AGENDAM    => p_cd_agendam
  );
  
  IF NOT p_erro THEN
    DBMS_OUTPUT.PUT_LINE('Cancelamento realizado com sucesso para o agendamento: ' || p_cd_agendam);
  ELSE
    DBMS_OUTPUT.PUT_LINE('Erro ao tentar cancelar o agendamento: ' || p_cd_agendam || ' - ' || p_erro_mt);
  END IF;
END;
/