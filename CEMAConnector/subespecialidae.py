subespecialidades_data = [
    {"VSUES_CD": " 1", "VSUES_DS": "GLAUCOMA "},
    {"VSUES_CD": " 2", "VSUES_DS": "CATARATA "},
    {"VSUES_CD": " 3", "VSUES_DS": "RETINA "},
    {"VSUES_CD": " 4", "VSUES_DS": "ESTRABISMO "},
    {"VSUES_CD": " 5", "VSUES_DS": "CORNEA CIRURGICO "},
    {"VSUES_CD": " 6", "VSUES_DS": "MIOPIA / REFRATIVA "},
    {"VSUES_CD": " 7", "VSUES_DS": "VITRECTOMIA "},
    {"VSUES_CD": " 8", "VSUES_DS": "HIPERTIROIDISMO "},
    {"VSUES_CD": " 9", "VSUES_DS": "TOXOPLASMOSE "},
    {"VSUES_CD": " 10", "VSUES_DS": "PROTESE OCULAR "},
    {"VSUES_CD": " 11", "VSUES_DS": "ALERGIA OCULAR "},
    {"VSUES_CD": " 12", "VSUES_DS": "BLEFARITE "},
    {"VSUES_CD": " 13", "VSUES_DS": "OLHOS SECOS "},
    {"VSUES_CD": " 14", "VSUES_DS": "PLASTICA OCULAR "},
    {"VSUES_CD": " 18", "VSUES_DS": "CERATOCONE "},
    {"VSUES_CD": " 19", "VSUES_DS": "ORBITA "},
    {"VSUES_CD": " 21", "VSUES_DS": "TRANSPLANTE CORNEA "},
    {"VSUES_CD": " 22", "VSUES_DS": "PALPEBRA "},
    {"VSUES_CD": " 26", "VSUES_DS": "VIA LACRIMAL "},
    {"VSUES_CD": " 27", "VSUES_DS": "TONOMETRIA "},
    {"VSUES_CD": " 28", "VSUES_DS": "PTERIGIO "},
    {"VSUES_CD": " 29", "VSUES_DS": "CALAZIO "},
    {"VSUES_CD": " 33", "VSUES_DS": "TUMOR PALPEBRAL "},
    {"VSUES_CD": " 35", "VSUES_DS": "CORNEA TRAT. CLINICA"},
    {"VSUES_CD": " 36", "VSUES_DS": "CROSS LINKING "},
    {"VSUES_CD": " 37", "VSUES_DS": "DEGENERAC?O MACULAR "},
    {"VSUES_CD": " 38", "VSUES_DS": "LENTE DE CONTATO "},
    {"VSUES_CD": " 39", "VSUES_DS": "OFTALMITITE "},
    {"VSUES_CD": " 40", "VSUES_DS": "BLEFAROESPASMO "},
    {"VSUES_CD": " 43", "VSUES_DS": "OFTALMOLOGIA GERAL "},
    {"VSUES_CD": " 44", "VSUES_DS": "PTOSE PALPEBRAL "},
    {"VSUES_CD": " 45", "VSUES_DS": "OCULOPLASTIA "},
    {"VSUES_CD": " 46", "VSUES_DS": "TESTE DE SCHIRMER "},
    {"VSUES_CD": " 47", "VSUES_DS": "ANEL INTRAESTROMAL "},
    {"VSUES_CD": " 50", "VSUES_DS": "TUMOR DE CONJUNTIVA "},
    {"VSUES_CD": " 51", "VSUES_DS": "ANEL INTRACORNEANO "},
    {"VSUES_CD": " 52", "VSUES_DS": "CIRURGIA REFRATIVA "},
    {"VSUES_CD": " 53", "VSUES_DS": "HORDEOLO "},
    {"VSUES_CD": " 54", "VSUES_DS": "INFLAMAC?O PALPEBRAL"},
    {"VSUES_CD": " 55", "VSUES_DS": "DOEN. CORNEA/CONJUNT"}
]

subespecialidades_dict = {item["VSUES_DS"].strip().upper(): item["VSUES_CD"].strip() for item in subespecialidades_data}