FROM python:3.7-alpine

RUN apk add  --no-cache ffmpeg
# Fix for Pillow https://github.com/python-pillow/Pillow/issues/1763#issuecomment-204252397
RUN apk add build-base jpeg-dev zlib-dev
ENV LIBRARY_PATH=/lib:/usr/lib

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