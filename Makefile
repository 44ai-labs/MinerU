
start:
	@echo "Starting the server..."
	PYTHONPATH=. MINERU_TOOLS_CONFIG_JSON=$$PWD/projects/web_server/magic-pdf-server.json python projects/web_server/server.py