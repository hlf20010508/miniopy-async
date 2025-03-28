#! /bin/bash

poetry run sphinx-apidoc -f -M --remove-old -o ./source/generated ../miniopy_async
poetry run make html
