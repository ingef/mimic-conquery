#!python3

# Argument Parser
import logging
from pathlib import Path

from common import log_request, JSON_HEADER, get_authorized_session, get_datasets, get_configured_arg_parser

parser = get_configured_arg_parser()
parser.add_argument('--files', nargs='*', help='tables that you want to upload')

arg_dict = vars(parser.parse_args())

datasets = get_datasets(arg_dict)

tables = arg_dict['tables']

api_url, session = get_authorized_session(arg_dict)

api_datasets = api_url + '/datasets'

for dataset in datasets:
    api_tables = f'{api_datasets}/{dataset.name}/tables'
    for table in map(Path, tables):

        if table.parent.parent.name == table:
            continue

        logging.debug(table)

        r = session.post(api_tables, data=table.open('rb'), headers=JSON_HEADER)
        msg = f'Upload table {dataset.name}.{table.name} with response {r.status_code}'
        log_request(msg, r)
