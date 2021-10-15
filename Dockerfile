FROM continuumio/miniconda3

LABEL Name=curator Version=3.3.5
WORKDIR /curator
COPY requirements.txt /curator

RUN apt-get update && apt-get install -y \
    libxrender-dev \
    && rm -rf /var/lib/apt/lists/*

RUN conda install -c conda-forge python=3.8 rdkit gunicorn libiconv && conda clean -afy

# Still run requirements install but should be fast if all installed
RUN pip install -r requirements.txt

ENV FLASK_APP "run.py"
ENV FLASK_CONFIG=production
ENV FLASK_ENV=production
EXPOSE 5000

RUN useradd -ms /bin/bash uwsgi

COPY app/ ./app/
COPY run.py celery_worker.py ./

CMD /bin/bash -c "gunicorn -w 4 -b 0.0.0.0:5000 run:app --access-logfile /dev/stdout --preload"
