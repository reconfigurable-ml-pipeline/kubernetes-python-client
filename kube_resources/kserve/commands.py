import time
from typing import List
from kserve import KServeClient

from kube_resources.utils import construct_inference_service, ContainerInfo

client = KServeClient()


def _get_inference_service_info(s: dict):
    predictor = s["spec"].get("predictor")
    transformer = s["spec"].get("transformer")
    return {
        "kind": "InferenceService",
        "namespace": s["metadata"]["namespace"],
        "name": s["metadata"]["name"],
        "terminating": s["metadata"].get("deletionTimestamp") is not None,
        "predictor": {
            "node": predictor.get("nodeName"),
            "containers": list(map(
                lambda c: {
                    "image": c["image"],
                    "ports": c["ports"],
                    "resources": {"requests": c["resources"]["requests"], "limits": c["resources"]["limits"]},
                    "env": c.get("env")
                },
                s["spec"]["predictor"]["containers"]
            ))
        } if predictor else None,
        "transformer": {
            "node": transformer("nodeName")
        } if transformer else None
    }


def get_inference_service(name: str, namespace="default"):
    response = client.get(name=name, namespace=namespace)
    return _get_inference_service_info(response)


def create_inference_service(
    inference_service_name: str,
    namespace="default",
    predictor_container: ContainerInfo = None,
    transformer_container: ContainerInfo = None,
    labels: dict = None,
    predictor_min_replicas: int = None,
    predictor_max_replicas: int = None,
    transformer_min_replicas: int = None,
    transformer_max_replicas: int = None,
    predictor_volumes: List[dict] = None,
    transformer_volumes: List[dict] = None,
    max_batch_size: int = None,
    max_batch_latency: int = None
):
    inference_service_obj = construct_inference_service(
        inference_service_name, 
        namespace,
        predictor_container=predictor_container,
        transformer_container=transformer_container,
        labels=labels,
        predictor_min_replicas=predictor_min_replicas,
        predictor_max_replicas=predictor_max_replicas,
        transformer_min_replicas=transformer_min_replicas,
        transformer_max_replicas=transformer_max_replicas,
        predictor_volumes=predictor_volumes,
        transformer_volumes=transformer_volumes,
        max_batch_size=max_batch_size,
        max_batch_latency=max_batch_latency
    )
    response = client.create(inference_service_obj, namespace)
    return get_inference_service(response["metadata"]["name"], namespace)


def patch_inference_service(
        inference_service_name: str,
        namespace="default",
        predictor_container: ContainerInfo = None,
        transformer_container: ContainerInfo = None,
        predictor_min_replicas: int = None,
        predictor_max_replicas: int = None,
        transformer_min_replicas: int = None,
        transformer_max_replicas: int = None,
        predictor_volumes: List[dict] = None,
        transformer_volumes: List[dict] = None,
        max_batch_size: int = None,
        max_batch_latency: int = None,
):

    isvc = construct_inference_service(
        inference_service_name,
        namespace,
        predictor_container=predictor_container,
        transformer_container=transformer_container,
        predictor_min_replicas=predictor_min_replicas,
        predictor_max_replicas=predictor_max_replicas,
        transformer_min_replicas=transformer_min_replicas,
        transformer_max_replicas=transformer_max_replicas,
        predictor_volumes=predictor_volumes,
        transformer_volumes=transformer_volumes,
        max_batch_size=max_batch_size,
        max_batch_latency=max_batch_latency
    )
    response = client.patch(inference_service_name, isvc, namespace=namespace)
    return get_inference_service(response["metadata"]["name"], namespace)


def delete_inference_service(inference_service_name: str, namespace="default"):
    response = client.delete(inference_service_name, namespace=namespace)
    return response["metadata"]["name"]
