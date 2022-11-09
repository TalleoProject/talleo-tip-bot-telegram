#!/bin/bash
pipenv requirements | sed 's/^-e \(.*\)#egg=\(.*\)/\2 @ \1/g' | grep -v '^\-i ' | cut -d ';' -f 1 - | sed 's/[[:blank:]]*$//' > requirements.txt
pipenv requirements --dev | sed 's/^-e \(.*\)#egg=\(.*\)/\2 @ \1/g' | grep -v '^\-i ' | cut -d ';' -f 1 - | sed 's/[[:blank:]]*$//' > requirements-dev.txt
