import argparse
import json
import logging
import os
import sys

from datetime import date
from loginterceptors import FailOnErrorHandler, UpgradeWarningToErrorFilter
from pathlib import Path
from requests import Response, Session
from typing import Tuple, Set, Optional, Iterable


def tostring(c):
    """
    Use this to get a nice __str__ for free
    """
    c.__str__ = lambda c: "%s(%s)" % (
        c.__class__.__name__,
        c.__dict__
    )
    return c


def remove_suffix(value: str, suffix: str) -> str:
    if not value.endswith(suffix):
        return value

    return value[:-len(suffix)]


def configure_logger(arg_dict):
    fast_fail = arg_dict['fast_fail']
    fail_on_warning = arg_dict['fail_on_warning']

    logging.basicConfig(
        level=os.environ.get("LOG_LEVEL", "INFO"),
        format='%(levelname)s\t[%(asctime)s]\t%(message)s',
        datefmt='%Y-%m-%d %I:%M:%S')

    if fail_on_warning:
        logging.getLogger().addFilter(UpgradeWarningToErrorFilter())

    logs: Path = arg_dict['log']

    # Log to file
    if logs:
        if not logs.exists():
            logs.mkdir(parents=True, exist_ok=True)

        if logs.is_dir():
            # If the destination is a folder append a file name to the
            logs = logs / f'{date.today()}.log'

        logging.getLogger().addHandler(logging.FileHandler(logs))

    # Register the fail handler at last so other handlers are able to receive the error before shutdown
    if fail_on_warning or fast_fail:
        logging.getLogger().addHandler(FailOnErrorHandler())


DEFAULT_TOKEN = os.environ.get('API_TOKEN')


class Dataset:
    name: str
    id: str
    label: str
    weight: int
    sources: Set[str] # Can be used as a meta-selector instead of dataset names

    def __init__(self, id: str, name: str, label: str, sources: Set[str], weight: int = 0):
        self.name = name
        self.id = id
        self.label = label
        self.weight = weight
        self.sources = set(sources)

    def __str__(self):
        return f"Dataset({self.name})"

    def __repr__(self):
        return f"Dataset({self.name})"

    def __hash__(self):
        return hash((self.__class__, self.name, self.label, self.weight, str(self.sources)))


def get_configured_arg_parser(with_api: bool = True, **kwargs) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(**kwargs)

    parser.add_argument('--datasets', nargs='*', help="Datasets you want to use.", default=[])

    parser.add_argument('--kassen', help='Meta data resource for the datasets to be created (datasets.json)',
                        default=Path(__file__).parent.parent / 'datasets.json', type=Path)

    parser.add_argument('--fast-fail', action='store_true', help="fails as soon as a requests returns a code >=400")
    parser.add_argument('--fail-on-warning', action='store_true', help="fails when a warning is produced")

    parser.add_argument('--log', help='File or directory to write the logs to.', type=Path)

    if with_api:
        parser.add_argument('--token', help='Authentication Token', default=DEFAULT_TOKEN)

        url_group = parser.add_mutually_exclusive_group()

        url_group.add_argument('--port', help='Admin API port, default is to read from env ${ADMIN_PORT}',
                               default=os.environ.get('ADMIN_PORT', 8081))

        url_group.add_argument('--server', help='Admin API URL.')

    return parser


def get_admin_api_url(arg_dict) -> str:
    if arg_dict["server"]:
        return arg_dict["server"] + "/admin"

    if arg_dict["port"]:
        return f"http://localhost:{arg_dict['port']}/admin"

    raise ValueError("Could not extract API Url from Args")


def log_request(msg, response: Optional[Response] = None):
    if response is not None and not response.ok:
        logging.error(msg)
        if response.content:
            logging.error(response.text)
    else:
        logging.info(msg)


def get_datasets(arg_dict) -> Set[Dataset]:
    def do_select(selection: Set[str], available: Set[Dataset]) -> Iterable[Dataset]:
        diff = selection.difference(dataset.id for dataset in available)
        diff = diff.difference(set.union(*[data.sources for data in available]))

        if diff:
            logging.error(f"Invalid datasets {diff}")
            sys.exit(1)

        for dataset in available:
            if dataset.id in selection:
                yield dataset

            if dataset.sources.intersection(selection):
                yield dataset

    datasets: Set[str] = set(arg_dict['datasets'])

    kassen_raw = json.load(arg_dict['kassen'].open("rb"))
    companies = {Dataset(id=dataset, **kassen_raw[dataset]) for dataset in kassen_raw.keys()}

    select = {sel for sel in datasets if not sel.startswith("^")}

    exclude = {sel[1:] for sel in datasets if sel.startswith("^")}

    if select:
        want = set(do_select(select, companies))
    else:
        want = companies

    if exclude:
        dont_want = set(do_select(exclude, companies))
        want = set(want.difference(dont_want))

    return want


def get_authorized_session(arg_dict) -> Tuple[str, Session]:
    session = Session()
    session.headers.update(get_auth_headers(arg_dict))

    return get_admin_api_url(arg_dict), session


def get_auth_headers(arg_dict):
    header = {'Cache-Control': 'no-cache'}
    if 'token' in arg_dict:
        header["Authorization"] = f"Bearer {arg_dict['token']}"
    return header


# TODO When all interactions with Conquery are migrated to json, this can be inlined above. ATM Form data causes issues.
JSON_HEADER = {'Content-Type': 'application/json'}
