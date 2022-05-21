#!/bin/bash
pipenv lock -r | grep -v '^\-i ' | cut -d ';' -f 1 - | cut -d ' ' -f 1 - > requirements.txt
pipenv lock -r --dev | grep -v '^\-i ' | cut -d ';' -f 1 - | cut -d ' ' -f 1 - > requirements-dev.txt
