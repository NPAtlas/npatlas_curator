FROM continuumio/miniconda3

LABEL Name=curator Version=3.2
WORKDIR /curator
COPY requirements.txt /curator

RUN apt-get update && apt-get install -y \
    libxrender-dev \
    && rm -rf /var/lib/apt/lists/*

RUN conda create -n curator -c conda-forge python=3.8 rdkit uwsgi libiconv

# Still run requirements install but should be fast if all installed
RUN /bin/bash -c "source activate curator && pip install -r requirements.txt"

ENV FLASK_APP "run.py"
ENV FLASK_CONFIG=production
ENV FLASK_ENV=production
EXPOSE 5000

RUN useradd -ms /bin/bash uwsgi

COPY app/ ./app/
COPY run.py celery_worker.py curator.ini ./

CMD /bin/bash -c "source activate curator && uwsgi --ini curator.ini"