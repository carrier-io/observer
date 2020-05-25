import os

from observer.app import create_parser, execute

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))


def test_main_with_data_params():
    args = create_parser().parse_args(
        [
            "-f", f"data.zip",
            # "-d", f"{ROOT_DIR}/data/data.json",
            "-sc", "/tmp/data/webmail.side",
            "-fp", "100",
            "-si", "400",
            "-tl", "500",
            "-r", "html",
            # "-g", "False"
        ])
    execute(args)


def test_list():
    test_scope = [{'id': 13, 'project_id': 1, 'test': 'webmail', 'environment': '',
                   'scope': 'Essential JS 2 for TypeScript - Webmail', 'metric': 50, 'target': 'total',
                   'aggregation': 'max', 'comparison': 'lte'}
                  ]
    every_scope = [{'id': 12, 'project_id': 1, 'test': 'webmail', 'environment': '', 'scope': 'every', 'metric': 100,
                    'target': 'total', 'aggregation': 'max', 'comparison': 'lt'},
                   {'id': 12, 'project_id': 1, 'test': 'webmail', 'environment': '', 'scope': 'every', 'metric': 100,
                    'target': 'time_to_paint', 'aggregation': 'max', 'comparison': 'lt'}]

    # for item in test_scope:
    #     every_scope = list(filter(lambda it: it['target'] != item['target'], every_scope))

    result = list({x['target']: x for x in every_scope + test_scope}.values())
    print(every_scope)
    test_scope.append(every_scope)

    print(test_scope)
