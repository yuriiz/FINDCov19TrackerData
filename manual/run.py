#!/usr/bin/env python3
import argparse
import concurrent.futures
import unittest
from json import dumps
from os import environ
from os.path import abspath, dirname
from urllib.request import Request, urlopen


def set_commit_status(status):
    token = environ.get('GITHUB_TOKEN')
    sha = environ.get('GITHUB_SHA')
    repo = environ.get('GITHUB_REPOSITORY')
    if token and sha and repo:
        return urlopen(
            Request(
                f'https://api.github.com/repos/{repo}/statuses/{sha}',
                dumps(status).encode('ascii'), {
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/vnd.github.v3+json",
                })).read()


def run_one_country(test_id):
    country = test_id.split('_')[-1].capitalize()
    status = {
        "state": "pending",
        "context": "Country: " + country
    }
    set_commit_status(status)
    suite = unittest.defaultTestLoader.loadTestsFromName(test_id)
    test, = list(suite)
    runner = unittest.TextTestRunner()
    result = runner.run(suite)
    status["state"] = "success" if result.wasSuccessful() else "failure"
    set_commit_status(status)
    return dict(country=country, **test.vars)


def all_test_ids(suite):
    result = []
    try:
        for s in suite:
            result += all_test_ids(s)
    except TypeError:
        result.append(suite.id())
    return result


if __name__ == '__main__':
    # collect list of all known countries
    # by enumerating all attributes of TestDefaultSuite starting with "test_"
    countries = all_test_ids(
        unittest.defaultTestLoader.discover(dirname(abspath(__file__))))
    # parse command line arguments
    parser = argparse.ArgumentParser(
        description='Run all or some tests.',
        epilog="If countries list omitted, will run tests for all countries.")
    parser.add_argument('countries',
                        nargs='*',
                        metavar='country',
                        choices=[c.split('_')[-1] for c in countries] + [[]],
                        help='Country name')
    country_list = []
    args = parser.parse_args()
    # run test(s)
    if args.countries:
        # run only countries specified in command line
        for country in args.countries:
            for test_id in countries:
                if test_id.endswith(country):
                    country_list.append(run_one_country(test_id))
    else:
        # run all countries in parallel
        with concurrent.futures.ThreadPoolExecutor() as executor:
            country_list = executor.map(run_one_country, countries)
    # save results
    with open("list_data.txt", 'w', encoding="utf-8") as f:
        for item in country_list:
            f.write("%s\n" % item)
        f.close()
