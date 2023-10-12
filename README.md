# pod-count-admission-controller
Sample implementation of validation webhook in kubernetes to restrict the number of pods.

## Admission Controller

This repository contains the implementation of ValidationAdmission controller that can intercept the pod creation request
and execute implemented logic for accepting or rejecting the pod request, based on the number of pods already running inside the pod.

## Why?

This is effectively the work of Controller(Deployment/StatefulSet) in kubernets to contorl the number of pods(replicas), however some of the use-cases we encountered had dynamic/run-time pod creation request without controller. To avoid starvation of resource due to spike in pod creation requests, we considered using ValidationWebhook.

## How it works?

- The decision of accepting or rejecting the request is based on the existing pod(s) in the provided namespace(in the creation request).
- The admission controller upon receving the request, reads the pod and namespace from the request.
- Then it reads the configuration map in the same namespace(configmap=quota-cm) with fixed key, that specific the maximum number of pods.
- Then it reads the pods in the existing namespace with give label(type=spark-executor-pod) and count the pods. 
- If the existing pod count is lower then the configured value in configmap then it accepts the request.
- If the pod count is equal or higher than configured on config-map, it rejects the request.

## How to Deploy?
- Run and created objects provided in manifests folder.
- Capture the token and get the certificate.
```
  openssl genrsa -out rootca.key 2048
  openssl req -x509 -sha256 -new -nodes -key  rootca.key  -days 3650 -out rootca.crt ## here make sure to provide the details that matches req.conf values. 
  openssl req -x509 -nodes -days 730 -newkey rsa:2048 -keyout security/webhook.key -out security/webhook.crt -config security/req.conf -extensions 'v3_req' -CA security/rootca.crt -CAkey security/rootca.key

  kubectl -n default create -f manifests/
  kubectl -n default get secret pod-checker-secret -o yaml -o jsonpath='{.data.token}' | base64 -d > security/token
  kubectl -n default get secret pod-checker-secret -o yaml -o jsonpath='{.data.ca\.crt}' | base64 -d > security/ca.crt 
  
  docker build -f . -t <repo>:latest
  docker push <repo>:latest
```
webhook-config.yaml
  Encode the rootca.crt file with base64 and provide it in caBundle before deploying webhook-config.yaml file.
webhook-deploy.yaml
  Update the image in webhook-deploy.yaml with the created and published image.
  Also update the KUBE_API_SERVER environment variable with correct api server IP and port.
webhook-secret.yaml
  Please encode the webhook.key and webhook.crt file with base64 and provide it in the webhook-secret.yaml

```

  kubectl create -f webhook-manifests

```

## Notes
If you are planning to use different namespace, make sure to change the DNS and hostname details in certificate and yaml files.