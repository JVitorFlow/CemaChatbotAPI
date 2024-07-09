SET SERVEROUTPUT ON SIZE UNLIMITED;

DECLARE
  p_erro BOOLEAN := FALSE;
  p_erro_cd NUMBER;
  p_erro_mt VARCHAR2(4000);
  p_recordset SYS_REFCURSOR;
  p_origem VARCHAR2(2) := 'C';
  p_patient_id NUMBER := {patient_id};
  p_vgpro_cd NUMBER := {vgpro_cd};
  p_vprre_cd NUMBER := {vprre_cd};
  v_unid_cd NUMBER;
  v_cocl_cd NUMBER;
  v_cocl_nm VARCHAR2(100);
  v_gpro_cd NUMBER;
  v_agma_cd NUMBER;
  v_dt DATE;
  v_hh NUMBER;
  v_mi NUMBER;
  v_cd_agendamento NUMBER;
BEGIN
  app_agd.VER_AGD_EXISTENTE(
    P_ERRO          => p_erro,
    P_ERRO_CD       => p_erro_cd,
    P_ERRO_MT       => p_erro_mt,
    P_RECORDSET     => p_recordset,
    P_ORIGEM        => p_origem,
    P_PATIENT_ID    => p_patient_id,
    P_vGPRO_CD      => p_vgpro_cd,
    P_vPRRE_CD      => p_vprre_cd
  );
  IF NOT p_erro THEN
    DBMS_OUTPUT.PUT_LINE('Consulta de agendamentos futuros iniciada...');
    LOOP
      FETCH p_recordset INTO v_unid_cd, v_cocl_cd, v_cocl_nm, v_gpro_cd, v_agma_cd, v_dt, v_hh, v_mi, v_cd_agendamento;
      EXIT WHEN p_recordset%NOTFOUND;
      DBMS_OUTPUT.PUT_LINE('Unidade_CD: ' || v_unid_cd);
      DBMS_OUTPUT.PUT_LINE('Medico: ' || v_cocl_nm);
      DBMS_OUTPUT.PUT_LINE('Data: ' || TO_CHAR(v_dt, 'DD-MM-YYYY'));
      DBMS_OUTPUT.PUT_LINE('Hora: ' || LPAD(v_hh, 2, '0') || ':' || LPAD(v_mi, 2, '0'));
      DBMS_OUTPUT.PUT_LINE('Agendamento_CD: ' || v_cd_agendamento);
      DBMS_OUTPUT.PUT_LINE('---');
    END LOOP;
    CLOSE p_recordset;
  ELSE
    DBMS_OUTPUT.PUT_LINE('Erro: ' || TO_CHAR(p_erro_cd) || ' - ' || p_erro_mt);
  END IF;
END;
/