#!python3

import logging
import re

# Argument Parser
from pathlib import Path
from typing import Optional

from requests.adapters import Response

from common import get_configured_arg_parser, get_datasets, log_request, get_authorized_session, configure_logger

parser = get_configured_arg_parser()

parser.add_argument('--update', help='Update cqpps.', action='store_true')
parser.add_argument('--dry', help='Dry run.', action='store_true')
parser.add_argument('--files', nargs='+')

arg_dict = vars(parser.parse_args())


configure_logger(arg_dict)

datasets = get_datasets(arg_dict)

dry = arg_dict['dry']

# extra dataset_id for alphabetically order in frontned

cqpps = arg_dict['files']

update_cqpps = arg_dict['update']

# set other variables
api_url, session = get_authorized_session(arg_dict)

#################################################################
# Import cqpps                                                  #
#################################################################

api_datasets = api_url + '/datasets'

# Import table with most distinct PIDs first for dictionary

method = "PUT" if update_cqpps else "POST"

for dataset in datasets:
    logging.info(f"BEGIN Processing {dataset}")
    for file in map(Path, cqpps):

        if file.parent.parent.name != dataset.id:
            continue

        match = file.name.split(".")

        if match[-1] != 'cqpp':
            continue

        if len(match) != 3:
            logging.warning(f"{file} not matching `$table.$tag.cqpp`")
            continue

        logging.info(f"Uploading `{file.name}` to `{dataset}`")

        table = match[0]
        tag = match[1]

        if not dry:
            resp = session.request(method, f"{api_datasets}/{dataset.name}/cqpp", data=file.open("rb"),
                                   headers={'Content-Type': 'application/octet-stream'})
        else:
            resp = None

        log_request(f"Uploading `{file}` to `{dataset}.{table}.{tag}`", resp)
