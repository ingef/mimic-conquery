#!/bin/bash

docker run -v ./datasets/imports/:/app/imports/ -v ./csv/:/app/csv -v ./cqpp/mimic:/app/cqpp  --rm ghcr.io/ingef/conquery-backend:develop preprocess --desc /app/imports --in /app/csv --out /app/cqpp