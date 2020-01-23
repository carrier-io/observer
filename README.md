# observer

Observer is a client for execution of UI performance tests as FaaS as well as from container

Work in progress

support only "url" as step, opens page and creates report
Validate against 3 possible thresholds: First paint, Total Load, Speed Index

```bash
docker run -it -v /tmp/reports:/tmp/reports \
       -e remote=10.23.8.210:4444 
       -e listener=10.23.8.210:9999 \
       getcarrier/observer:latest \
           -s "{\"url\": \"https://www.google.com\", \"el\": \"//img[@tag=\\\"Google\\\"]\"}" \
           -s "{\"url\": \"https://www.youtube.com\"}" \
           -fp 100 -si 400 -tl 500 -r xml -r html
```