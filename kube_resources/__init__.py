import os
import json
from kubernetes import client, config
from kubernetes.client.api_client import ApiClient


class VPAApiClient(ApiClient):
    def deserialize(self, response, response_type):
        if response_type == "json":
            return json.loads(response.data)
        return super().deserialize(response, response_type)
    

if os.environ.get("K8S_IN_CLUSTER_CLIENT", "").lower() == "true":
    config.load_incluster_config()
else:
    config.load_kube_config()

core_api = client.CoreV1Api()
apps_api = client.AppsV1Api()
autoscaling_api = client.AutoscalingV1Api()
vpa_api = client.AutoscalingV1Api(api_client=VPAApiClient())
custom_api = client.CustomObjectsApi()
