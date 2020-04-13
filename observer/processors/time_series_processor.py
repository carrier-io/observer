import json
import os
import re
import time
from urllib.parse import urlparse

from observer.constants import exporters_path


def export_to_telegraph_json(raw_data):
    # https://github.com/influxdata/telegraf/tree/master/plugins/serializers/json

    resources = raw_data['performanceResources']
    perf_timing = raw_data['performancetiming']
    timing = raw_data['timing']

    requests = count_request_number(resources)
    domains = count_unique_domain_number(resources)
    total_load_time = perf_timing['loadEventEnd'] - perf_timing['navigationStart']
    speed_index = timing['speedIndex']
    time_to_first_byte = perf_timing['responseStart'] - perf_timing['navigationStart']
    time_to_first_paint = timing['firstPaint']
    dom_content_loading = perf_timing['domContentLoadedEventStart'] - perf_timing['domLoading']
    dom_processing = perf_timing['domComplete'] - perf_timing['domLoading']

    result = {
        "fields": {
            "requests": len(requests),
            "domains": len(domains),
            "total": total_load_time,
            "speed_index": speed_index,
            "time_to_first_byte": time_to_first_byte,
            "time_to_first_paint": time_to_first_paint,
            "dom_content_loading": dom_content_loading,
            "dom_processing": dom_processing
        },
        "name": raw_data['info']['title'],
        "tags": {},
        "timestamp": time.time()
    }
    os.makedirs(exporters_path, exist_ok=True)
    with open(os.path.join(exporters_path, 'data.json'), 'w') as outfile:
        json.dump(result, outfile, indent=4)
    return json.dumps(result)


def count_request_number(resources):
    return list(filter(
        lambda x: not re.match(r'/http[s]?:\/\/(micmro|nurun).github.io\/performance-bookmarklet\/.*/', x['name']),
        resources))


def count_unique_domain_number(resources):
    result = set()
    for e in resources:
        url = urlparse(e['name'])
        result.add(url.netloc)
    return result
