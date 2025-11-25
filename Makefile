test:
# Makefile pour lightspeed2mqtt

.PHONY: help run test


help:
	@echo "Options disponibles :"
	@echo "  make run           : lancer l'application (simple-logi.py)"
	@echo "  make test          : lancer tous les tests (pytest tests)"
	@echo "  make add_service   : installer le service Windows via nssm"
	@echo "  make remove_service: désinstaller le service Windows via nssm"
	@echo "  make stop_service  : arrêter le service Windows via nssm"
	@echo "  make help          : afficher cette aide"


# Variables pour le service
SERVICE_NAME = "LightSpeedMan"
PYTHON_PATH = $(CURDIR)\.venv\Scripts\python.exe
SCRIPT_PATH = $(CURDIR)\simple-logi.py
WORKDIR = $(CURDIR)
# Chemin NSSM à adapter si besoin
NSSM_PATH = "C:\nssm\nssm.exe"

add_service:
	@echo Installation du service Windows via NSSM...
	@powershell -NoProfile -Command "& '$(NSSM_PATH)' install $(SERVICE_NAME) '$(PYTHON_PATH)' '$(SCRIPT_PATH)'"
	@powershell -NoProfile -Command "& '$(NSSM_PATH)' set $(SERVICE_NAME) AppDirectory '$(WORKDIR)'"
	@powershell -NoProfile -Command "& '$(NSSM_PATH)' start $(SERVICE_NAME)"
	@echo Service installé et démarré.

remove_service:
	@echo Suppression du service Windows via NSSM...
	@powershell -NoProfile -Command "& '$(NSSM_PATH)' stop $(SERVICE_NAME)"
	@powershell -NoProfile -Command "& '$(NSSM_PATH)' remove $(SERVICE_NAME) confirm"
	@echo Service supprimé.

stop_service:
	@echo Arrêt du service Windows via NSSM...
	@powershell -NoProfile -Command "& '$(NSSM_PATH)' stop $(SERVICE_NAME)"
	@echo Service arrêté.

run:
	python simple-logi.py

test:
	pytest tests

.DEFAULT_GOAL := help
