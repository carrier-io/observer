import os

from junit_xml import TestSuite, TestCase

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


def test_can_generate_junit_report():
    failed_case = TestCase("threshold", "observer", 1244, '', '')
    failed_case.add_failure_info("threshold failed")
    test_cases = [
        TestCase("threshold", "observer", 1234, '', ''),
        failed_case
    ]

    ts = TestSuite("Observer UI Benchmarking Test ", test_cases)
    with open(f"report_{1}.xml", 'w') as f:
        TestSuite.to_file(f, [ts], prettyprint=True)
