# Use uma imagem base do Python 3.10
FROM python:3.10

# Instale as dependências necessárias do sistema
RUN apt-get update && apt-get install -y \
    libaio1 \
    libaio-dev \
    unzip \
    wget \
    build-essential

# Crie o diretório de trabalho
WORKDIR /var/www/html

# Instale o virtualenv
RUN pip install --upgrade pip
RUN pip install virtualenv

# Crie e ative o ambiente virtual
RUN virtualenv venv
ENV VIRTUAL_ENV /var/www/html/venv
ENV PATH /var/www/html/venv/bin:$PATH

# Copie os arquivos de requisitos
COPY requirements.txt .

# Instale as dependências do Python no ambiente virtual
RUN /var/www/html/venv/bin/pip install --no-cache-dir -r requirements.txt

# Criar o diretório staticfiles
RUN mkdir -p /var/www/html/staticfiles

# Crie um diretório temporário para o Gunicorn
RUN mkdir -p /var/www/html/temp

# Copie o código da aplicação para o contêiner
COPY . .

# Colete os arquivos estáticos
RUN python manage.py collectstatic --noinput

# Exponha a porta da aplicação
EXPOSE 8000

# Comando para iniciar o Gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "CEMAConnector.wsgi:application"]
