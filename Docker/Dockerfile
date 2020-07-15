FROM continuumio/miniconda3

LABEL Name=curator Version=3.1
WORKDIR /curator
COPY requirements.txt /curator

RUN conda create -n curator -c rdkit rdkit

# Still run requirements install but should be fast if all installed
RUN /bin/bash -c "source activate curator && pip install -r requirements.txt"

ENV FLASK_APP "run.py"
ENV FLASK_CONFIG=production
ENV FLASK_ENV=production
EXPOSE 5000

RUN apt-get update && apt-get install -y libxrender-dev
RUN /bin/bash -c "source activate curator && conda install -c conda-forge uwsgi libiconv"
RUN useradd -ms /bin/bash uwsgi

COPY app/ ./app/
COPY run.py config.py celery_worker.py curator.ini ./

CMD /bin/bash -c "source activate curator && uwsgi --ini curator.ini"
