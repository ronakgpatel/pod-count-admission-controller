import sys
import os
import requests
import kubernetes
import json
from kubernetes.stream import stream
from pprint import pprint
from kubernetes import client, config, watch
from kubernetes.client.rest import ApiException
from flask import Flask, request, jsonify
import logging

webhook = Flask(__name__)
webhook.logger.setLevel(logging.INFO)
CHECK_LABEL_KEY="type"
CHECK_LABEL_VALUE="my-pod-value"

def admission_response(allowed, uid, message):
    return jsonify({"apiVersion": "admission.k8s.io/v1",
                    "kind": "AdmissionReview",
                    "response":
                        {"allowed": allowed,
                         "uid": uid,
                         "status": {"message": message}
                         }
                    })


@webhook.route('/validate', methods=['POST'])
def validate_request():
    request_info = request.get_json()
    return validate(request_info)

def validate(request_info):
        uid = request_info["request"].get("uid")
        i_request = request_info["request"]        
        pod = i_request["object"]
        pod_name = pod["metadata"]["name"]
        pod_namespace = pod["metadata"]["namespace"]
        webhook.logger.info(f"Validating admission for pod : {pod_name} in {pod_namespace} namespace")        
        pod_label = [CHECK_LABEL_KEY]
        if CHECK_LABEL_KEY not in pod["metadata"]["labels"]:
            webhook.logger.info(f"Pod does not have label with key type, skipping check")
            return admission_response(True, uid, f"Pod does not have label with key type, skipping admission check")

        tokenFile = "token"
        caFile = "ca.crt"

        if os.path.exists( tokenFile ) :
            token_file = open( tokenFile )
            aToken = token_file.readline().rstrip()
        else :
            webhook.logger.error(f"Error: Token File - %s doesn't exists. Aborting Connection - {tokenFile}")
            sys.exit(1)

        if os.path.exists( caFile ) :
            ca_File = open( caFile )
            aCertFile = ca_File.readline().rstrip()
        else :
            webhook.logger.error(f"Error: Cert File - %s doesn't exists. Aborting Connection - {caFile}")
            sys.exit(1)              

        aConfiguration = client.Configuration()
        aConfiguration.host = os.environ.get('KUBE_API_SERVER', "https://localhost:443")
        aConfiguration.verify_ssl = False

        aConfiguration.api_key = {"authorization": "Bearer " + aToken}
        aApiClient = client.ApiClient(aConfiguration)
        v1 = client.CoreV1Api(aApiClient)

        MAX_PODS_ALLOWED=2
        
        try:
            api_response = v1.read_namespaced_config_map("quota-cm", pod_namespace )
            webhook.logger.warn(f"Max Pods Allowed (from config map) :  {api_response.data['MAX_PODS_ALLOWED']}")
            MAX_PODS_ALLOWED=int(api_response.data['MAX_PODS_ALLOWED'])

        except ApiException as e:
            obj = json.loads(e.body)
            webhook.logger.error(f"Exception while calling CoreV1Api->read_namespaced_config_map: %s\n {e}")
            sys.exit(1)
              
        total_pods=0
        try:
            ret = v1.list_namespaced_pod(pod_namespace)
            if len(ret.items) > 0:
                for i in ret.items:
                    #skip the pods which does not have the labels
                    if CHECK_LABEL_KEY in i.metadata.labels and i.metadata.labels[CHECK_LABEL_KEY].lower() == CHECK_LABEL_VALUE:
                        total_pods+=1                        
            else:
                print("No pods in the namespace, continuing")            
        except ApiException as e:
            webhook.logger.error("Exception while getting pod label : %s\n {e}")
            sys.exit(1)     
      
        if(total_pods >= MAX_PODS_ALLOWED):
            webhook.logger.warn(f"Existing pods {total_pods} are already equal or higher than {MAX_PODS_ALLOWED}")
            return admission_response(False, uid, f"Existing pods {total_pods} are already equal or higher than {MAX_PODS_ALLOWED}")
       
        webhook.logger.info(f"Existing pods {total_pods} are lower than {MAX_PODS_ALLOWED}, continuing the pod admission")
        return admission_response(True, uid, f"Existing pods {total_pods} are lower than {MAX_PODS_ALLOWED}, continuing the pod admission")              

if __name__ == '__main__':
    webhook.run(host='0.0.0.0', port=5005)