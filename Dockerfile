FROM alpine:3.12 as alpine
ENV PYTHONUNBUFFERED=1
ENV RUN_IN_DOCKER=yes
ENV DEBUG_MODE=no
ENV CHECK_POOL=no 

RUN mkdir /app
RUN mkdir /app/nginx
WORKDIR /app
ADD requirements.txt /app
RUN apk add --no-cache \
    git \
    ca-certificates \
    tzdata \
    python3 \
    py3-pip \
    docker-cli \
    openrc \
    py-pip python3-dev libffi-dev openssl-dev gcc libc-dev make curl

RUN apk add --update \
  build-base \
  cairo \
  cairo-dev \
  cargo \
  freetype-dev \
  gcc \
  gdk-pixbuf-dev \
  gettext \
  jpeg-dev \
  lcms2-dev \
  libffi-dev \
  musl-dev \
  openjpeg-dev \
  openssl-dev \
  pango-dev \
  poppler-utils \
  postgresql-client \
  postgresql-dev \
  py-cffi \
  python3-dev \
  rust \
  tcl-dev \
  tiff-dev \
  tk-dev \
  zlib-dev

RUN ln -sf python3 /usr/bin/python
RUN python3 -m ensurepip
RUN python3 -m pip install --upgrade pip
RUN pip3 install --upgrade setuptools docker-compose
RUN pip3 install -r requirements.txt
RUN pip3 install --upgrade --no-deps --force-reinstall git+https://github.com/shellcodesniper/aws_logging_handlers.git

ADD . /app

CMD ["python3", "main.py"]