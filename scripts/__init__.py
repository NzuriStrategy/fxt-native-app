# scripts/ — standalone CLI entry points for the lead intelligence pipeline.
#
# Each script is self-contained and importable from the project root:
#
#   poetry run python scripts/ingest_csv.py --csv data/sample_companies.csv
#
# Scripts add the project root to sys.path so they work without installing
# the package in editable mode.
