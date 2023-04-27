#!python3

import aiohttp
import asyncio
import gzip
import logging
import sys
import time

from asyncio import Semaphore
from pathlib import Path
from requests import Response, Session
from typing import Any, Dict, List, Set, Optional

from actions.actions_def import Action, exclude_tag
from actions.parse_arguments import configure_arg_parser_for_actions, get_request
from common import (
    JSON_HEADER,
    Dataset,
    configure_logger,
    get_auth_headers,
    get_authorized_session,
    get_configured_arg_parser,
    get_datasets,
    log_request,
    remove_suffix,
)


def main_request():
    # Here is the order of execution for the actions defined.
    actions_ordered = [
        Action("dataset", create_dataset),
        Action("mapping", upload_mappings),
        Action("secondaryid", create_secondary_ids),
        Action("search", upload_search_index),
        Action("table", create_tables),
        Action("concept", create_concepts),
        Action("cqpp", upload_cqpps),
        Action("structure", upload_structures),
        Action("preview", add_preview_config),
        Action("decoding", upload_id_mappings),
        Action("update", submit_update_matching_stats),
    ]

    # Argument Parser
    parser = get_configured_arg_parser()
    configure_arg_parser_for_actions(
        parser, {act.name for act in actions_ordered}, exclude_tag
    )

    parser.add_argument("--cqpp", help="Root folder of preprocessed files.", type=Path)
    parser.add_argument("--decode", help="Root folder of PID-decode files.", type=Path)
    parser.add_argument(
        "--json",
        help="Root folder of json files that will be created/used.",
        default="./gen",
        type=Path,
    )
    parser.add_argument(
        "--parallelism",
        help="Number of threads per Dataset to upload CQPPs. If None, will upload sequentially for all datasets, so at least 1 is recommended.",
        type=int,
        default=None,
    )

    arg_dict = vars(parser.parse_args())

    configure_logger(arg_dict)

    request: Set[str] = {
        act.name for act in get_request(arg_dict, actions_ordered, exclude_tag)
    }

    data_dir: Path = arg_dict["cqpp"]

    parallel: Optional[int] = arg_dict["parallelism"]

    api_url, session = get_authorized_session(arg_dict)

    logging.debug(arg_dict)

    if parallel and parallel < 1:
        logging.error("Need at least one thread per Dataset.")
        sys.exit(1)

    failures: List[Response] = []

    remaining = len(request)
    selection = get_datasets(arg_dict)

    for action in actions_ordered:
        if action.name in request:
            failures.extend(action.callable(
                arg_dict=arg_dict,
                data_dir=data_dir,
                decoding_dir=arg_dict.get("decode", data_dir),
                json_dir=arg_dict["json"],
                parallel=parallel,
                datasets=selection,
                session=session,
                api_datasets=api_url + "/datasets",
            ))

            remaining -= 1
            # If this is the last action, we do not have to wait
            if remaining > 0:
                time.sleep(5)

    if not failures:
        sys.exit(0)

    sep = "\n\t"

    errors = [response.text for response in failures if response.content]

    logging.error(f"Failed with {len(failures)} errors: {sep.join(errors)}")
    sys.exit(1)


def create_dataset(
        datasets: Set[Dataset],
        session: Session,
        api_datasets: str,
        **_,  # ignore remaining keyword arguments
) -> List[Response]:  # This action doesn't return any failures, only an empty List
    logging.info(f"BEGIN Uploading datasets {datasets}")

    for dataset in datasets:
        # add dataset
        resp = session.post(
            api_datasets,
            json={
                "name": dataset.name,
                "label": dataset.label,
                "weight": dataset.weight,
            },
            headers=JSON_HEADER,
        )

        msg = f"Creating dataset {dataset.name}"
        log_request(msg=msg, response=resp)

    return []  # This action doesn't return any failures


def add_preview_config(
        datasets: Set[Dataset],
        session: Session,
        api_datasets: str,
        json_dir: Path,
        **_,  # ignore remaining keyword arguments
) -> List[Response]:
    failures: List[Response] = []
    for dataset in datasets:
        api_preview = f"{api_datasets}/{dataset.name}/preview"
        preview = json_dir / dataset.id / f"preview.json"

        resp = session.post(api_preview, data=preview.open("rb"), headers=JSON_HEADER)

        msg = f"Upload preview for {dataset.name} with response {resp.status_code}"
        log_request(msg=msg, response=resp)

        if not resp.ok:
            failures.append(resp)

    return failures


def create_secondary_ids(
        datasets: Set[Dataset],
        session: Session,
        api_datasets: str,
        json_dir: Path,
        **_,  # ignore remaining keyword arguments
) -> List[Response]:
    failures: List[Response] = []

    for dataset in datasets:
        api_secondary_ids = f"{api_datasets}/{dataset.name}/secondaryId"

        for secondary_id in (json_dir / dataset.id / "secondaryIds").glob("*.json"):

            resp = session.post(
                api_secondary_ids, data=secondary_id.open("rb"), headers=JSON_HEADER
            )

            secondary_id_name = remove_suffix(secondary_id.name, ".import.json")
            msg = f"Upload secondaryId {dataset.name}.{secondary_id_name} with response {resp.status_code}"
            log_request(msg=msg, response=resp)

            if not resp.ok:
                failures.append(resp)

    return failures


def upload_mappings(
        datasets: Set[Dataset],
        session: Session,
        api_datasets: str,
        json_dir: Path,
        **_,  # ignore remaining keyword arguments
) -> List[Response]:
    failures: List[Response] = []

    for dataset in datasets:
        api = f"{api_datasets}/{dataset.name}/internToExtern"

        for id in (json_dir / dataset.id / "mappings").glob("*.json"):

            resp = session.post(
                api, data=id.open("rb"), headers=JSON_HEADER
            )

            name = remove_suffix(id.name, ".mapping.json")
            msg = f"Upload internToExtern mapping {dataset.name}.{name} with response {resp.status_code}"
            log_request(msg=msg, response=resp)

            if not resp.ok:
                failures.append(resp)

    return failures


def upload_search_index(
        datasets: Set[Dataset],
        session: Session,
        api_datasets: str,
        json_dir: Path,
        **_,  # ignore remaining keyword arguments
) -> List[Response]:
    failures: List[Response] = []

    for dataset in datasets:
        api = f"{api_datasets}/{dataset.name}/searchIndex"

        for id in (json_dir / dataset.id / "searchIndex").glob("*.json"):

            resp = session.post(
                api, data=id.open("rb"), headers=JSON_HEADER
            )

            name = remove_suffix(id.name, ".filter.json")
            msg = f"Upload search index mapping {dataset.name}.{name} with response {resp.status_code}"
            log_request(msg=msg, response=resp)

            if not resp.ok:
                failures.append(resp)

    return failures


def create_tables(
        datasets: Set[Dataset],
        session: Session,
        api_datasets: str,
        json_dir: Path,
        **_,  # ignore remaining keyword arguments
) -> List[Response]:
    failures: List[Response] = []

    for dataset in datasets:
        for table_file in (json_dir / dataset.id / "tables").glob("*.table.json"):

            api_tables = f"{api_datasets}/{dataset.name}/tables"

            resp = session.post(
                api_tables, data=table_file.open("rb"), headers=JSON_HEADER
            )

            table_file_name = remove_suffix(table_file.name, ".table.json")
            msg = f"Upload table {dataset.name}.{table_file_name} with response {resp.status_code}"
            log_request(msg=msg, response=resp)

            if not resp.ok:
                failures.append(resp)

    return failures


def create_concepts(
        datasets: Set[Dataset],
        session: Session,
        api_datasets: str,
        json_dir: Path,
        **_,  # ignore remaining keyword arguments
) -> List[Response]:
    failures: List[Response] = []

    for dataset in datasets:
        api_concepts = f"{api_datasets}/{dataset.name}/concepts"

        for concept in (json_dir / dataset.id / "concepts").glob("*.concept.json"):

            resp = session.post(
                api_concepts, data=concept.open("rb"), headers=JSON_HEADER
            )

            concept_name = remove_suffix(concept.name, ".concept.json")
            msg = f"Upload concept {dataset.name}.{concept_name} with response {resp.status_code}"
            log_request(msg=msg, response=resp)

            if not resp.ok:
                failures.append(resp)

    return failures


def upload_cqpps(
        arg_dict: Dict[str, Any],
        datasets: Set[Dataset],
        parallel: Optional[int],
        api_datasets: str,
        data_dir: Path,
        **_,  # ignore remaining keyword arguments
) -> List[Response]:  # This action doesn't return any failures, only an empty List
    async def upload_cqpp(
            dataset: Dataset,
            cqpp: Path,
            session: aiohttp.ClientSession,
            semaphores: Dict[Dataset, Semaphore],
    ):

        api_cqpps = f"{api_datasets}/{dataset.name}/cqpp"

        async with semaphores[dataset]:
            with open(cqpp, "rb") as data:
                try:
                    async with session.post(
                            api_cqpps,
                            data=data,
                            headers={"Content-Type": "application/octet-stream"},
                    ) as resp:
                        await resp.text()
                        logging.info(f"Uploaded cqpp {cqpp}")
                except Exception as err:
                    logging.warning(f"Failed to upload Cqpp {cqpp}:{err}")

    async def do_upload(
            loop: asyncio.AbstractEventLoop, datasets: Set[Dataset], parallel: Optional[int]
    ) -> None:
        aio_session: aiohttp.ClientSession

        async with aiohttp.ClientSession(
                headers=get_auth_headers(arg_dict)
        ) as aio_session:

            if parallel:
                slots = int(parallel)
                logging.info(f"Uploading to {datasets} using {parallel} per dataset")
            else:
                single_semaphore = Semaphore(1)

            # If parallelism is set, distribute it evenly among datasets,
            # else return single_semaphore for all, making this single_threaded.
            dataset_semaphores: Dict[Dataset, Semaphore] = {
                dataset: Semaphore(slots) if parallel else single_semaphore
                for dataset in datasets
            }

            tasks: List[asyncio.Task] = []

            for dataset in datasets:
                for cqpp in (data_dir / dataset.id / "cqpp/").glob("*.cqpp"):
                    tasks.append(
                        loop.create_task(
                            upload_cqpp(dataset, cqpp, aio_session, dataset_semaphores)
                        )
                    )

            await asyncio.gather(*tasks)

    loop = asyncio.new_event_loop()

    loop.run_until_complete(do_upload(loop, datasets, parallel))

    loop.close()

    return []  # This action doesn't return any failures


def upload_structures(
        datasets: Set[Dataset],
        session: Session,
        api_datasets: str,
        json_dir: Path,
        **_,  # ignore remaining keyword arguments
) -> List[Response]:
    failures: List[Response] = []

    for dataset in datasets:
        api_structure = f"{api_datasets}/{dataset.name}/structure"

        with open(
                str(json_dir / dataset.id / f"structure_{dataset.id}.json"), "rb"
        ) as data:
            resp = session.post(api_structure, data=data, headers=JSON_HEADER)

            msg = f"Upload structure json for dataset {dataset.id} with response {resp.status_code}"
            log_request(msg=msg, response=resp)

            if not resp.ok:
                failures.append(resp)

    return failures


def upload_id_mappings(
        datasets: Set[Dataset],
        session: Session,
        decoding_dir: Path,
        api_datasets: str,
        **_,  # ignore remaining keyword arguments
) -> List[Response]:
    headers = {"Content-Type": "application/octet-stream"}

    for dataset in datasets:

        if "adb" not in dataset.sources:
            continue

        decodings = list((decoding_dir / dataset.id / "csv").glob("decoding.*.csv.gz"))

        if len(decodings) != 1:
            raise ValueError(
                f"Found {len(decodings)} files. Need exactly one. (dir = {decoding_dir})"
            )

        decoding = decodings[0]

        with gzip.open(decoding, "rb") as data:
            resp = session.post(
                f"{api_datasets}/{dataset.name}/mapping", headers=headers, data=data
            )

            msg = f"Upload decoding file {decoding} for dataset {dataset} with response {resp.status_code}"
            log_request(msg=msg, response=resp)

    return []  # This action doesn't return any failures


def submit_update_matching_stats(
        datasets: Set[Dataset],
        session: Session,
        api_datasets: str,
        **_,  # ignore remaining keyword arguments
) -> List[Response]:
    logging.info("Submit UpdateMatchingStats")

    failures: List[Response] = []

    for dataset in datasets:
        api_update = f"{api_datasets}/{dataset.name}/update-matching-stats"

        resp = session.post(api_update)

        msg = f"Execute updateMatchingStats for dataset {dataset.name} with responds {resp.status_code}"
        log_request(msg=msg, response=resp)

        if not resp.ok:
            failures.append(resp)

    return failures


if __name__ == "__main__":
    main_request()
