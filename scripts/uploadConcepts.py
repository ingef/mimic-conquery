#!python3
import time
import logging

# Argument Parser
from pathlib import Path

from common import log_request, JSON_HEADER, remove_suffix, get_authorized_session, get_datasets, \
    get_configured_arg_parser, configure_logger

parser = get_configured_arg_parser()

parser.add_argument('--files', nargs='*', help='concepts that you want to upload')
parser.add_argument('--update', action='store_true', help='Update existing concepts')

arg_dict = vars(parser.parse_args())

configure_logger(arg_dict)

datasets = get_datasets(arg_dict)

concepts = arg_dict['concepts']
update = arg_dict['update']

logging.debug(concepts)

# Set logging

api_url, session = get_authorized_session(arg_dict)

api_datasets = api_url + '/datasets'

for dataset in datasets:
    api_concepts = f'{api_datasets}/{dataset.name}/concepts'
    for concept in map(Path, concepts):

        if dataset.id != concept.parent.parent.name:
            continue

        concept_name = remove_suffix(concept.name, '.concept.json')

        data = open(concept, 'rb')
        if update :
            r = session.put(api_concepts, data=data, headers=JSON_HEADER)
            msg = f'Updated concept {dataset.name}.{concept_name} with response {r.status_code}'
        else:
            r = session.post(api_concepts, data=data, headers=JSON_HEADER)
            msg = f'Upload concept {dataset.name}.{concept_name} with response {r.status_code}'
        log_request(msg, r)
