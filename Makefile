
start:
	@echo "Starting the server..."
	PYTHONPATH=. MINERU_TOOLS_CONFIG_JSON=$$PWD/projects/web_server/magic-pdf-server.json python projects/web_server/server.py

download-paddle-models:
	@echo "Downloading Paddle models..."
	@echo "We do that by running one file that will download all the models."
	PYTHONPATH=. MINERU_TOOLS_CONFIG_JSON=$$PWD/projects/web_server/magic-pdf-server-non-gpu.json python projects/web_server/simple_test.py