# observer

Observer is a client for execution of UI performance tests as FaaS as well as from container

Work in progress

support only "url" as step, opens page and creates report
Validate against 3 possible thresholds: First paint, Total Load, Speed Index

Start chrome and wait until it is ready

```bash
docker run --name chrome getcarrier/observer-chrome:latest
```

```bash
docker run -it -e remote=chrome:4444 -e listener=chrome:9999 -e token=${GALLOPER_AUTH_TOKEN}  \
-v /tmp/reports:/tmp/reports -v ${PWD}/data:/data --link=chrome \
getcarrier/observer:latest -f webmail.side -sc /data/webmail.side -r html -fp 100 -si 400 -tl 500
```

if you want to run it locally without integration with galloper add -g 'False' flag
