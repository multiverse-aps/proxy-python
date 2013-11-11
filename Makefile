all: clean-pyc test

clean-pyc:
	find . -name '*.pyc' -exec rm -f {} +
	find . -name '*.pyo' -exec rm -f {} +
	find . -name '*~' -exec rm -f {} +

test:
	@nosetests -s -w tests

test_setup:
	@python scripts/test_setup.py

toxtest:
	@tox

.PHONY: test clean-pyc all
