FROM python:3.7-alpine

RUN apk add  --no-cache ffmpeg

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