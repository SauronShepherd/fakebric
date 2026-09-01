param(
  [string]$Profile = "minikube",
  [string]$Context = "minikube",
  [string]$ApiImage = "fakebric:dev-20260831-v15",
  [string]$ControllerImage = "fakebric/controller:dev-20260901-v13",
  [string]$RuntimeImage = "fakebric/runtime:1.3-20260901-v5"
)
$ErrorActionPreference = "Stop"

minikube start --profile $Profile
docker build -q -t $ApiImage . | Out-Host
docker build -q -f controller.Dockerfile -t $ControllerImage . | Out-Host
docker build -q -f runtime/Dockerfile -t $RuntimeImage . | Out-Host
minikube image load $ApiImage --profile=$Profile
minikube image load $ControllerImage --profile=$Profile
minikube image load $RuntimeImage --profile=$Profile
kubectl --context=$Context apply -f k8s
kubectl --context=$Context -n fakebric-system set image deployment/fakebric-api api=$ApiImage
kubectl --context=$Context -n fakebric-system set image deployment/fakebric-session-controller controller=$ControllerImage
kubectl --context=$Context -n fakebric-system rollout status deployment/fakebric-api --timeout=120s
kubectl --context=$Context -n fakebric-system rollout status deployment/fakebric-session-controller --timeout=120s
kubectl --context=$Context -n fakebric-system get pods
