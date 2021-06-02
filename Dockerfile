FROM python:3.7-alpine

RUN apk add  --no-cache ffmpeg
# Fix for Pillow https://github.com/python-pillow/Pillow/issues/1763#issuecomment-204252397
RUN apk add build-base jpeg-dev zlib-dev
ENV LIBRARY_PATH=/lib:/usr/lib
ENV CRYPTOGRAPHY_DONT_BUILD_RUST=1

# Fix for cryptography https://stackoverflow.com/questions/35736598/cannot-pip-install-cryptography-in-docker-alpine-linux-3-3-with-openssl-1-0-2g
RUN apk add --no-cache \
        libressl-dev \
        musl-dev \
        libffi-dev && \
    pip install --no-cache-dir cryptography && \
    apk del \
        libressl-dev \
        musl-dev \
        libffi-dev

RUN pip install --upgrade pip
RUN pip install --upgrade setuptools
ADD MANIFEST.in /tmp/MANIFEST.in

ADD setup.py /tmp/setup.py
ADD requirements.txt /tmp/requirements.txt
COPY observer /tmp/observer
RUN cd /tmp && python setup.py install && rm -rf /tmp/*

RUN mkdir /tmp/reports
WORKDIR /tmp
SHELL ["/bin/bash", "-c"]
EXPOSE 5000
ENTRYPOINT ["app"]