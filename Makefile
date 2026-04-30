SHELL := /bin/bash

PROJECT_NAME ?= nlv-search
COMPOSE ?= docker compose
ENV_FILE ?= .env
ENV_SOPS ?= .env.sops
ENV_EXAMPLE ?= .env.example
SOPS_AGE_KEY_FILE ?= $(HOME)/.age/key.txt
TEST_IMAGE_PREFIX ?= nlv
LAST_TEST_LOG ?= last-test-logs.txt
INTEGRATION_COMPOSE_SERVICES ?= postgres-nlv-search minio-nlv-search qdrant-nlv-search redis-nlv-search tei-nlv-search ai-nlv-search backend-nlv-search
BACKEND_TEST_URL ?= http://backend-$(PROJECT_NAME):8000
AI_TEST_URL ?= http://ai-$(PROJECT_NAME):8501

.PHONY: ensure-env up down logs test clean restart \
        env-encrypt env-decrypt env-decrypt-force env-edit env-status

define RESET_TEST_LOG
	@if [ -z "$(TEST_LOG_APPEND)" ]; then : > "$(LAST_TEST_LOG)"; fi
endef

define RUN_AND_LOG
	@cmd='$(subst ','"'"',$(1))'; \
	printf '$$ %s\n' "$$cmd" | tee -a "$(LAST_TEST_LOG)"; \
	bash -o pipefail -c "$$cmd" 2>&1 | tee -a "$(LAST_TEST_LOG)"; \
	status=$${PIPESTATUS[0]}; \
	if [ $$status -eq 5 ] && [ "$(strip $(2))" = "true" ]; then \
		echo "pytest selected no matching tests; continuing" | tee -a "$(LAST_TEST_LOG)"; \
		exit 0; \
	fi; \
	exit $$status
endef

define RUN_UNIT_TESTS
	$(call RUN_AND_LOG,docker build --build-arg INSTALL_DEV=true -t $(TEST_IMAGE_PREFIX)-$(1)-tests $(PROJECT_NAME)/$(1))
	$(call RUN_AND_LOG,docker run --rm --env-file $(ENV_FILE) $(TEST_IMAGE_PREFIX)-$(1)-tests pytest -m "not integration",$(2))
endef

define RUN_INTEGRATION_TESTS
	$(call RUN_AND_LOG,docker build --build-arg INSTALL_DEV=true -t $(TEST_IMAGE_PREFIX)-$(1)-tests $(PROJECT_NAME)/$(1))
	$(call RUN_AND_LOG,docker run --rm --env-file $(ENV_FILE) --env BACKEND_URL=$(2) --env AI_URL=$(AI_TEST_URL) --network $(PROJECT_NAME)_$(PROJECT_NAME)-net --add-host host.docker.internal:host-gateway $(TEST_IMAGE_PREFIX)-$(1)-tests pytest -m integration,$(3))
endef

## ── Environment ──────────────────────────────────────────────────────────────

# Расшифровать .env.sops → .env (если .env отсутствует)
env-decrypt:
	@if [ ! -f $(ENV_FILE) ]; then \
		echo "Decrypting $(ENV_SOPS) → $(ENV_FILE)"; \
		SOPS_AGE_KEY_FILE=$(SOPS_AGE_KEY_FILE) sops --input-type dotenv --output-type dotenv -d $(ENV_SOPS) > $(ENV_FILE); \
		echo "Done. $(ENV_FILE) created."; \
	else \
		echo "$(ENV_FILE) already exists, skipping. Use 'make env-decrypt-force' to overwrite."; \
	fi

# Расшифровать принудительно (перезаписать .env)
env-decrypt-force:
	SOPS_AGE_KEY_FILE=$(SOPS_AGE_KEY_FILE) sops --input-type dotenv --output-type dotenv -d $(ENV_SOPS) > $(ENV_FILE)
	@echo "$(ENV_FILE) updated."

# Зашифровать .env → .env.sops (после ручного редактирования .env)
env-encrypt:
	@if [ ! -f $(ENV_FILE) ]; then echo "No $(ENV_FILE) found"; exit 1; fi
	SOPS_AGE_KEY_FILE=$(SOPS_AGE_KEY_FILE) sops --input-type dotenv --output-type dotenv -e $(ENV_FILE) > $(ENV_SOPS)
	@echo "Encrypted → $(ENV_SOPS). Don't forget: git add $(ENV_SOPS)"

# Открыть .env в редакторе и сразу перешифровать после закрытия
env-edit:
	@if [ ! -f $(ENV_FILE) ]; then \
		SOPS_AGE_KEY_FILE=$(SOPS_AGE_KEY_FILE) sops --input-type dotenv --output-type dotenv -d $(ENV_SOPS) > $(ENV_FILE); \
	fi
	$${EDITOR:-nano} $(ENV_FILE)
	SOPS_AGE_KEY_FILE=$(SOPS_AGE_KEY_FILE) sops --input-type dotenv --output-type dotenv -e $(ENV_FILE) > $(ENV_SOPS)
	@echo "Re-encrypted → $(ENV_SOPS). Don't forget: git add $(ENV_SOPS)"

# Показать статус: есть ли .env, .env.sops, age key
env-status:
	@echo "=== Environment status ==="
	@[ -f $(ENV_FILE) ]     && echo "  ✓ $(ENV_FILE) exists"          || echo "  ✗ $(ENV_FILE) missing"
	@[ -f $(ENV_SOPS) ]     && echo "  ✓ $(ENV_SOPS) exists"          || echo "  ✗ $(ENV_SOPS) missing"
	@[ -f $(ENV_EXAMPLE) ]  && echo "  ✓ $(ENV_EXAMPLE) exists"       || echo "  ✗ $(ENV_EXAMPLE) missing"
	@[ -f $(SOPS_AGE_KEY_FILE) ] && echo "  ✓ age key found"          || echo "  ✗ age key missing ($(SOPS_AGE_KEY_FILE))"

ensure-env: env-decrypt

## ── Docker Compose ───────────────────────────────────────────────────────────

up: ensure-env
	$(COMPOSE) up --build -d

down:
	$(COMPOSE) down

logs:
	$(COMPOSE) logs -f

clean:
	$(COMPOSE) down -v --remove-orphans
	docker system prune -af

restart: ensure-env
	$(COMPOSE) down -v --remove-orphans
	$(COMPOSE) up --build -d

## ── Tests ────────────────────────────────────────────────────────────────────

test: ensure-env
	$(RESET_TEST_LOG)
	$(call RUN_UNIT_TESTS,backend)
	$(call RUN_UNIT_TESTS,ai,true)
	$(call RUN_AND_LOG,$(COMPOSE) up --build -d $(INTEGRATION_COMPOSE_SERVICES))
	$(call RUN_AND_LOG,POSTGRES_USER=$$(sed -n 's/^POSTGRES_USER=//p' $(ENV_FILE) | head -n1); POSTGRES_DB=$$(sed -n 's/^POSTGRES_DB=//p' $(ENV_FILE) | head -n1); TEI_PORT=$$(sed -n 's/^TEI_PORT=//p' $(ENV_FILE) | head -n1); AI_PORT=$$(sed -n 's/^AI_PORT=//p' $(ENV_FILE) | head -n1); BACKEND_PUBLISHED_PORT=$$(sed -n 's/^BACKEND_PUBLISHED_PORT=//p' $(ENV_FILE) | head -n1); wait_url() { for i in $$(seq 1 60); do curl -fsS "$$1" >/dev/null 2>&1 && return 0; sleep 2; done; echo "Timeout: $$1"; return 1; }; until $(COMPOSE) exec -T postgres-nlv-search pg_isready -U "$${POSTGRES_USER:-postgres}" -d "$${POSTGRES_DB:-postgres}" >/dev/null 2>&1; do sleep 2; done; wait_url "http://127.0.0.1:$${TEI_PORT:-8080}/health"; wait_url "http://127.0.0.1:$${AI_PORT:-8501}/health/"; wait_url "http://127.0.0.1:$${BACKEND_PUBLISHED_PORT:-8000}/health/")
	$(call RUN_INTEGRATION_TESTS,backend,$(BACKEND_TEST_URL))
	$(call RUN_INTEGRATION_TESTS,ai,$(BACKEND_TEST_URL))
