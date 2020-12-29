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
    ca-certificates \
    tzdata \
    python3 \
    py3-pip \
    docker-cli \
    openrc \
    py-pip python3-dev libffi-dev openssl-dev gcc libc-dev make curl

RUN ln -sf python3 /usr/bin/python
RUN python3 -m ensurepip
RUN pip3 install --no-cache --upgrade pip setuptools docker-compose
RUN pip3 install -r requirements.txt

ADD . /app

CMD ["python3", "main.py"]