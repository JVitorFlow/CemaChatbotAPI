unidade_mapping = {
    'BELEM': {'codigo': 1, 'nome': 'BELEM'},
    'SANTANA': {'codigo': 17, 'nome': 'SANTANA'},
    'ARICANDUVA': {'codigo': 19, 'nome': 'ARICANDUVA'},
    'INTERLAGOS': {'codigo': 20, 'nome': 'INTERLAGOS'},
    'TUCURUVI': {'codigo': 21, 'nome': 'TUCURUVI'},
    'ELDORADO': {'codigo': 22, 'nome': 'ELDORADO'},
    'S.BERNARDO': {'codigo': 23, 'nome': 'S.BERNARDO'},
    'ITAQUERA': {'codigo': 24, 'nome': 'ITAQUERA'},
    'W.PLAZA': {'codigo': 25, 'nome': 'W.PLAZA'},
    'GUARULHOS': {'codigo': 26, 'nome': 'GUARULHOS'},
    'OSASCO': {'codigo': 28, 'nome': 'OSASCO'},
    'IBIRAPUERA': {'codigo': 31, 'nome': 'IBIRAPUERA'}
}

def get_unidade_by_codigo(codigo):
    """
    Retorna o nome da unidade com base no código fornecido.

    :param codigo: Código da unidade.
    :return: Nome da unidade se encontrado, caso contrário None.
    """
    for key, value in unidade_mapping.items():
        if value['codigo'] == codigo:
            return value['nome']
    return None

def get_unidade_by_nome(nome):
    """
    Retorna o código da unidade com base no nome fornecido.

    :param nome: Nome da unidade.
    :return: Código da unidade se encontrado, caso contrário None.
    """
    unidade = unidade_mapping.get(nome.upper())
    if unidade:
        return unidade['codigo']
    return None
