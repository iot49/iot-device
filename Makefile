tag:
	git tag ${TAG} -m "${MSG}"
	git push --tags

dist:
	python3 setup.py sdist bdist_wheel

publish-test: clean dist
	twine upload --repository-url https://test.pypi.org/legacy/ dist/*

# login: t_m/O_5
publish: clean dist
	twine upload dist/*

install-local: clean dist
	python setup.py install

test:
	rm -rf tests/projects
	cd tests; pytest iot_device
#   cd tests; pytest iot_device_old
#   cd tests; pytest airlift

coverage: test
	coverage report

docs:
	cd docs; make html
	open docs/_build/html/index.html

clean:
	rm -rf dist
	rm -rf *egg-info
	rm -rf iot_device/__pycache__
