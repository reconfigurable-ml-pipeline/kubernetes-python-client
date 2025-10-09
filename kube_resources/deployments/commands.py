import time
from typing import List
from kubernetes.client.models import V1Deployment

from kube_resources.utils import construct_deployment, ContainerInfo
from kube_resources import apps_api as api


def _get_deployment_info(deployment: V1Deployment):
    return {
        "kind": "Deployment",
        "namespace": deployment.metadata.namespace,
        "name": deployment.metadata.name,
        "replicas": deployment.spec.replicas,
        "selector": {
            "match_labels": deployment.spec.selector.match_labels,
            "match_expressions": deployment.spec.selector.match_expressions
        },
        "rolling_update_strategy": {
            "max_surge": deployment.spec.strategy.rolling_update.max_surge,
            "max_unavailable": deployment.spec.strategy.rolling_update.max_unavailable,
        },
        "containers": list(map(
            lambda c: {
                "name": c.name,
                "image": c.image,
                "ports": c.ports,
                "resources": {
                    "limits": c.resources.limits,
                    "requests": c.resources.requests
                }
            },
            deployment.spec.template.spec.containers
        )),
        "status": {
            "available_replicas": deployment.status.available_replicas,
            "replicas": deployment.status.replicas,
            "ready_replicas": deployment.status.ready_replicas,
            "updated_replicas": deployment.status.updated_replicas,
        }
    }


def create_deployment(
        name: str,
        containers: List[ContainerInfo],
        replicas: int,
        namespace="default",
        labels: dict = None,
        annotations: dict = None,
        volumes: List[dict] = None,
        restart_policy: str = None,
        scheduler_name: str = None,
):
    deployment = construct_deployment(
        name=name,
        namespace=namespace,
        containers=containers,
        replicas=replicas,
        labels=labels,
        annotations=annotations,
        volumes=volumes,
        restart_policy=restart_policy,
        scheduler_name=scheduler_name,
    )
    response = api.create_namespaced_deployment(namespace=namespace, body=deployment)
    return get_deployment(response.metadata.name, namespace)


def get_deployments(namespace="default"):
    if namespace == "all":
        response = api.list_deployment_for_all_namespaces(watch=False)
    else:
        response = api.list_namespaced_deployment(namespace, watch=False)
    return list(
        map(
            lambda d: _get_deployment_info(d),
            response.items
        )
    )


def get_deployment(name, namespace="default"):
    response = api.read_namespaced_deployment(name=name, namespace=namespace)
    return _get_deployment_info(response)


def update_deployment(
        name: str,
        containers: List[ContainerInfo],
        replicas: int = None,
        labels: dict = None,
        volumes: List[dict] = None,
        partial=True,
        restart_policy: str = None,
        namespace="default"
):
    deployment = api.read_namespaced_deployment(name=name, namespace=namespace)  # type: V1Deployment
    deployment = construct_deployment(
        name=name,
        namespace=deployment.metadata.namespace,
        containers=containers,
        replicas=replicas,
        labels=labels,
        volumes=volumes,
        restart_policy=restart_policy
    )
    if partial:
        response = api.patch_namespaced_deployment(name=name, namespace=namespace, body=deployment)
    else:
        response = api.replace_namespaced_deployment(name=name, namespace=namespace, body=deployment)
    return get_deployment(response.metadata.name, namespace)


def delete_deployment(deployment_name, namespace="default"):
    response = api.delete_namespaced_deployment(name=deployment_name, namespace=namespace)
    return {"status": response.status}
