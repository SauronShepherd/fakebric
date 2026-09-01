MINIKUBE_PROFILE ?= minikube
KUBE_CONTEXT ?= minikube
API_IMAGE ?= fakebric:dev-20260831-v15
CONTROLLER_IMAGE ?= fakebric/controller:dev-20260901-v13
RUNTIME_IMAGE ?= fakebric/runtime:1.3-20260901-v5

.PHONY: check test production-gate doctor minikube-up dev-install dev-up dev-down dev-reset dev-test runtime-build controller-build k8s-apply backup-apply
check: test
production-gate:
	python tools/production_gate.py
doctor:
	@where python
	@where docker
	@where kubectl
	@where minikube
test:
	python -m pytest -q --cov=fakebric --cov-report=term-missing --cov-fail-under=75
minikube-up:
	minikube start --profile $(MINIKUBE_PROFILE)
dev-install:
	minikube image build -t $(API_IMAGE) -p $(MINIKUBE_PROFILE) .
	docker build -f runtime/Dockerfile -t $(RUNTIME_IMAGE) .
	docker build -f controller.Dockerfile -t $(CONTROLLER_IMAGE) .
	minikube image load $(RUNTIME_IMAGE) -p $(MINIKUBE_PROFILE)
	minikube image load $(CONTROLLER_IMAGE) -p $(MINIKUBE_PROFILE)
	kubectl --context=$(KUBE_CONTEXT) apply -f k8s/deployment.yaml

dev-up: dev-install k8s-apply backup-apply

dev-down:
	kubectl --context=$(KUBE_CONTEXT) delete namespace fakebric-system --ignore-not-found

dev-reset: dev-down
	minikube delete -p $(MINIKUBE_PROFILE)
	minikube start -p $(MINIKUBE_PROFILE) --driver=docker
dev-test:
	kubectl --context=$(KUBE_CONTEXT) -n fakebric-system rollout status deployment/fakebric-api --timeout=120s
	kubectl --context=$(KUBE_CONTEXT) -n fakebric-system run smoke --rm -i --restart=Never --image=curlimages/curl -- curl -fsS http://fakebric-api:8000/healthz

runtime-build:
	docker build -f runtime/Dockerfile -t $(RUNTIME_IMAGE) .

controller-build:
	docker build -f controller.Dockerfile -t $(CONTROLLER_IMAGE) .

k8s-apply:
	kubectl --context=$(KUBE_CONTEXT) apply -f k8s/deployment.yaml -f k8s/controller-rbac.yaml -f k8s/controller-deployment.yaml -f k8s/api-pdb.yaml -f k8s/session-networkpolicy.yaml

backup-apply:
	kubectl --context=$(KUBE_CONTEXT) apply -f k8s/backup.yaml
