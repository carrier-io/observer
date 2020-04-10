import json
import os
import time

from observer.constants import exporters_path


def export_to_telegraph_json(raw_data):
    # https://github.com/influxdata/telegraf/tree/master/plugins/serializers/json
    result = {"fields": {"demo": "2"}, "name": "", "tags": {}, "timestamp": time.time()}
    with open(os.path.join(exporters_path, 'data.json'), 'w') as outfile:
        json.dump(result, outfile, indent=4)
    return json.dumps(result)
