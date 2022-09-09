import time
from typing import List
from kserve import KServeClient

from kube_resources.utils import construct_inference_service

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


def create_inference_service(inference_service_name: str, namespace="default", **kwargs):
    inference_service_obj = construct_inference_service(inference_service_name, namespace, **kwargs)
    response = client.create(inference_service_obj, namespace)
    time.sleep(1)
    return get_inference_service(response["metadata"]["name"], namespace)


def patch_inference_service(
        inference_service_name: str,
        namespace="default",
        predictor_request_mem: str = None,
        predictor_request_cpu: str = None,
        transformer_request_mem: str = None,
        transformer_request_cpu: str = None,
        predictor_limit_mem: str = None,
        predictor_limit_cpu: str = None,
        predictor_limit_gpu: str = None,
        transformer_limit_mem: str = None,
        transformer_limit_cpu: str = None,
        predictor_args: List[str] = None,
        transformer_args: List[str] = None,
        predictor_min_replicas: int = None,
        predictor_max_replicas: int = None,
        transformer_min_replicas: int = None,
        transformer_max_replicas: int = None,
        max_batch_size: int = None,
        max_batch_latency: int = None,
):

    isvc = construct_inference_service(
        inference_service_name,
        namespace,
        predictor_request_mem=predictor_request_mem,
        predictor_request_cpu=predictor_request_cpu,
        transformer_request_mem=transformer_request_mem,
        transformer_request_cpu=transformer_request_cpu,
        predictor_limit_mem=predictor_limit_mem,
        predictor_limit_cpu=predictor_limit_cpu,
        predictor_limit_gpu=predictor_limit_gpu,
        transformer_limit_mem=transformer_limit_mem,
        transformer_limit_cpu=transformer_limit_cpu,
        predictor_args=predictor_args,
        transformer_args=transformer_args,
        predictor_min_replicas=predictor_min_replicas,
        predictor_max_replicas=predictor_max_replicas,
        transformer_min_replicas=transformer_min_replicas,
        transformer_max_replicas=transformer_max_replicas,
        max_batch_size=max_batch_size,
        max_batch_latency=max_batch_latency
    )
    response = client.patch(inference_service_name, isvc, namespace=namespace)
    time.sleep(1)
    return get_inference_service(response["metadata"]["name"], namespace)


def delete_inference_service(inference_service_name: str, namespace="default"):
    response = client.delete(inference_service_name, namespace=namespace)
    return response["metadata"]["name"]
