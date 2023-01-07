import os
from kubernetes import client, config


if os.environ.get("K8S_IN_CLUSTER_CLIENT", "").lower() == "true":
    config.load_incluster_config()
else:
    config.load_kube_config()
core_api = client.CoreV1Api()
apps_api = client.AppsV1Api()
autoscaling_api = client.AutoscalingV1Api()
custom_api = client.CustomObjectsApi()
