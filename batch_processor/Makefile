.PHONY: clean

clean:
	@echo -e "\033[1;90mCleaning up...\033[0m"
	@find . -type f -name '*.py[co]' -delete
	@find . -type d -name __pycache__ -delete
	@find . -type d -name .ipynb_checkpoints -exec rm -rf {} +
	@rm -rf build/ dist/ .eggs/
	@find . -name '*.egg-info' -exec rm -rf {} +
	@rm -f .coverage*
	@rm -rf .pytest_cache
	@rm -rf htmlcov/ coverage.xml
