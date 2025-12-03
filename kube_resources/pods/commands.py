import time
from typing import List, Callable
from kubernetes.client.models import V1Pod, V1ContainerStatus
from kube_resources import core_api as api
from kube_resources.utils import construct_pod, ContainerInfo


def _get_pod_info(p: V1Pod):
    container_statuses: Callable[[V1Pod], List[V1ContainerStatus]] = lambda pod: pod.status.container_statuses or []
    
    return {
        "kind": "Pod",
        "pod_ip": p.status.pod_ip,
        "namespace": p.metadata.namespace,
        "name": p.metadata.name,
        "node": p.spec.node_name,
        "containers": [
            {k: getattr(container, k) for k in container.attribute_map}
            for container in p.spec.containers
        ],
        "labels": p.metadata.labels,
        "phase": p.status.phase,
        "annotations": p.metadata.annotations,
        "conditions": list(map(
            lambda x: {"reason": x.reason, "type": x.type, "message": x.message}, p.status.conditions
        )) if p.status.conditions else [],
        "terminating": p.metadata.deletion_timestamp is not None,
        "restart_policy": p.spec.restart_policy,
        "container_statuses": list(map(
            lambda c: {
                "container_name": c.name,
                "image": c.image,
                "started": c.started,
                "state": {
                    "running": {
                        "started_at": c.state.running.started_at.isoformat()
                    } if c.state.running else None,
                    "terminated": {
                        "finished_at": c.state.terminated.finished_at.isoformat(),
                        "exit_code": c.state.terminated.exit_code,
                        "message": c.state.terminated.message,
                        "reason": c.state.terminated.reason,
                    } if c.state.terminated else None,
                    "waiting": {
                        "message": c.state.waiting.message,
                        "reason": c.state.waiting.reason
                    } if c.state.waiting else None,
                },
                "last_state": {
                    "running": {
                        "started_at": c.last_state.running.started_at.isoformat()
                    } if c.last_state.running else None,
                    "terminated": {
                        "finished_at": c.last_state.terminated.finished_at.isoformat(),
                        "exit_code": c.last_state.terminated.exit_code,
                        "message": c.last_state.terminated.message,
                        "reason": c.last_state.terminated.reason,
                    } if c.last_state.terminated else None,
                    "waiting": {
                        "message": c.last_state.waiting.message,
                        "reason": c.last_state.waiting.reason
                    } if c.last_state.waiting else None,
                }
            }, container_statuses(p)
        )),
    }


def create_pod(
        name: str,
        containers: List[ContainerInfo],
        namespace="default",
        labels: dict = None,
        annotations: dict = None,
        volumes: List[dict] = None,
        restart_policy: str = None,
        scheduler_name: str = None,
        runtime_class_name: str = None,
):
    pod = construct_pod(
        name=name,
        namespace=namespace,
        containers=containers,
        labels=labels,
        annotations=annotations,
        volumes=volumes,
        restart_policy=restart_policy,
        scheduler_name=scheduler_name,
        runtime_class_name=runtime_class_name,
    )
    response = api.create_namespaced_pod(
        namespace=namespace, body=pod
    )
    return get_pod(response.metadata.name, namespace)


def get_pods(namespace="default"):
    if namespace == "all":
        pods = api.list_pod_for_all_namespaces(watch=False)
    else:
        pods = api.list_namespaced_pod(namespace, watch=False)
    return {
        "kind": pods.kind,
        "pods": list(map(lambda p: _get_pod_info(p), pods.items))
    }


def get_pod(pod_name, namespace="default"):
    response = api.read_namespaced_pod(name=pod_name, namespace=namespace)
    return _get_pod_info(response)


def update_pod(
        name,
        containers: List[ContainerInfo],
        labels: dict = None,
        annotations: dict = None,
        volumes: List[dict] = None,
        partial=True,
        resize=True,
        namespace="default",
        restart_policy: str = None,
):
    pod = api.read_namespaced_pod(name=name, namespace=namespace)  # type: V1Pod
    pod = construct_pod(
        name,
        namespace=pod.metadata.namespace,
        containers=containers,
        labels=labels,
        annotations=annotations,
        volumes=volumes,
        restart_policy=restart_policy
    )
    if partial:
        if resize:
            response = api.patch_namespaced_pod_resize(name=name, namespace=namespace, body=pod)
        else:
            response = api.patch_namespaced_pod(name=name, namespace=namespace, body=pod)
    else:
        response = api.replace_namespaced_pod(name=name, namespace=namespace, body=pod)
    return get_pod(response.metadata.name, namespace=namespace)


def delete_pod(pod_name, namespace="default"):
    response = api.delete_namespaced_pod(name=pod_name, namespace=namespace)
    return {"status": response.status}
