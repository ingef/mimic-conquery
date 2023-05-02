This repository is based on the MIMIC-IV dataset. 

To get more expressive queries, we join admissions with patients, and admissions with diagnoses_icd.

The resulting files need to be placed in `cqpp/mimic` and the filenames need to correspond to the sourceFile-names in their respective import.json files. You will then run `preprocess.sh` to preprocess the files from csv to cqpp files for import into conquery.

To load the files use `scripts/request.py`, which will by default execute all import-actions, though you will only need `dataset table concept cqpp update`. The last of which will trigger a scan on the loaded dataset to give an overview for the users.

These steps should be sufficient to get a minimal conquery instance going based on the MIMIC-IV dataset.