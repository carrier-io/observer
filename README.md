# observer

Observer is a client for execution of UI performance tests as FaaS as well as from container

Start chrome and wait until it is ready

```bash
docker run --name chrome getcarrier/observer-chrome:latest
```

```bash
docker run -it -e REMOTE_URL=chrome:4444 -e LISTENER_URL=chrome:9999 -e token=${GALLOPER_AUTH_TOKEN}  \
-v /tmp/reports:/tmp/reports -v ${PWD}/data:/data --link=chrome \
getcarrier/observer:latest -f data.zip -sc /tmp/data/webmail.side \
-r junit -l 1 -a max
```

Supported reporters:

- Html (default)
- JIRA
- AzureDevops
- Junit XML


if you want to run it locally without integration with galloper add -g 'False' flag
