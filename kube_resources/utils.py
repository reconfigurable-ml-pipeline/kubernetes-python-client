from typing import List, TypedDict, Optional

from kubernetes.client import (
    V1Pod, V1EnvVar, V1EnvVarSource, V1ConfigMapKeySelector, V1ResourceRequirements, V1ObjectMeta, V1PodSpec,
    V1Container, V1ContainerPort, V1Deployment, V1DeploymentSpec, V1LabelSelector, V1PodTemplateSpec, V1Service,
    V1ServiceSpec, V1ServicePort, V1HorizontalPodAutoscaler, V1HorizontalPodAutoscalerSpec,
    V1CrossVersionObjectReference, V1ConfigMap, V1Volume, V1VolumeMount, V1ConfigMapVolumeSource,
    V1NFSVolumeSource, V1EmptyDirVolumeSource, V1Probe, V1ExecAction, V1HTTPGetAction
)
from kserve import (
    V1beta1InferenceService, V1beta1InferenceServiceSpec, V1beta1PredictorSpec, V1beta1TransformerSpec, V1beta1Batcher
)
from kserve.constants import constants


class ContainerInfo(TypedDict):
    name: str
    image: str
    request_mem: str
    request_cpu: str
    limit_mem: str
    limit_cpu: str
    limit_gpu: Optional[str]
    env_vars: Optional[dict]
    container_ports: Optional[List[int]]
    command: Optional[str]
    args: Optional[List[str]]
    volume_mounts: Optional[List[dict]]
    readiness_probe: Optional[dict]
    image_pull_policy: Optional[str]


def _construct_container(container_info: ContainerInfo) -> V1Container:
    container_kwargs = {"name": container_info["name"], "image": container_info["image"], "image_pull_policy": container_info.get("image_pull_policy")}
    if container_info.get("container_ports"):
        container_kwargs.update(
            {"ports": list(map(lambda p: V1ContainerPort(container_port=p), container_info["container_ports"]))}
        )
    if container_info.get("command"):
        container_kwargs.update({"command": [container_info["command"]]})
    if container_info.get("args"):
        container_kwargs.update({"args": container_info["args"]})
    if container_info.get("env_vars") is None:
        container_info["env_vars"] = {}
    container_info["env_vars"] = list(map(
        lambda t: V1EnvVar(
            t[0],
            (
                lambda x: str(x) if not isinstance(x, dict) else V1EnvVarSource(
                    config_map_key_ref=V1ConfigMapKeySelector(name=x["name"], key=x["key"])
                )
            )(t[1])
        ), container_info["env_vars"].items()
    ))
    limits = {}
    requests = {}
    if container_info.get("limit_mem"):
        limits.update(memory=container_info["limit_mem"])
    if container_info.get("limit_cpu"):
        limits.update(cpu=container_info["limit_cpu"])
    if container_info.get("limit_gpu"):
        limits.update({"nvidia.com/gpu": container_info["limit_gpu"]})
    if container_info.get("request_mem"):
        requests.update(memory=container_info["request_mem"])
    if container_info.get("request_cpu"):
        requests.update(cpu=container_info["request_cpu"])
    if requests or limits:
        container_kwargs.update(resources=V1ResourceRequirements(limits=limits or None, requests=requests or None))
    if container_info["env_vars"]:
        container_kwargs.update(env=container_info["env_vars"])

    mounts = []
    if container_info.get("volume_mounts"):
        for vm in container_info["volume_mounts"]:
            mounts.append(V1VolumeMount(**vm))
        container_kwargs.update(volume_mounts=mounts)
    
    if container_info.get("readiness_probe"):
        rp = container_info["readiness_probe"]
        rp_kwargs = dict(
            initial_delay_seconds=rp.get("initial_delay_seconds"),
            period_seconds=rp.get("period_seconds"),
            timeout_seconds=rp.get("timeout_seconds"),
            success_threshold=rp.get("success_threshold")
        )
        if rp.get("exec"):
            rp_kwargs["_exec"] = V1ExecAction(command=rp["exec"])
        elif rp.get("http_get"):
            rp_kwargs["http_get"] = V1HTTPGetAction(path=rp["http_get"].get("path"), port=rp["http_get"]["port"])
        else:
            pass  # Todo: Add other types of probes
        container_kwargs.update(readiness_probe=V1Probe(**rp_kwargs))
    return V1Container(**container_kwargs)


def _construct_volume(config: dict):
    # Fixme: currently only allowing ConfigMap, NFS and emptyDir Volume types

    if config.get("config_map"):
        v = V1Volume(
            name=config["name"],
            config_map=V1ConfigMapVolumeSource(**config["config_map"])
        )
    elif config.get("nfs"):
        v = V1Volume(
            name=config["name"],
            nfs=V1NFSVolumeSource(**config["nfs"])
        )
    elif config.get("empty_dir"):
        v = V1Volume(
            name=config["name"],
            empty_dir=V1EmptyDirVolumeSource()
        )
    else:
        v = None
    return v

def construct_pod(
        name: str,
        namespace: str,
        containers: List[ContainerInfo],
        *,
        labels: dict = None,
        volumes: List[dict] = None,
        restart_policy: str = None
) -> V1Pod:
    if labels is None:
        labels = {}
    pod = V1Pod(
        "v1",
        "Pod",
        metadata=V1ObjectMeta(name=name, namespace=namespace, labels=labels),
        spec=V1PodSpec(
            containers=[_construct_container(ci) for ci in containers],
            volumes=[_construct_volume(v) for v in volumes] if volumes else None,
            restart_policy=restart_policy,
        )
    )
    return pod


def construct_deployment(
        name: str,
        namespace: str,
        containers: List[ContainerInfo],
        replicas: int,
        *,
        labels: dict = None,
        volumes: List[dict] = None,
        restart_policy: str = None,
) -> V1Deployment:
    pod = construct_pod(
        name,
        namespace,
        containers,
        labels=labels,
        volumes=volumes,
        restart_policy=restart_policy,
    )

    deployment = V1Deployment(
        api_version="apps/v1",
        kind="Deployment",
        metadata=V1ObjectMeta(name=name, namespace=namespace),
        spec=V1DeploymentSpec(
            replicas=replicas,
            selector=V1LabelSelector(match_labels=pod.metadata.labels),
            template=V1PodTemplateSpec(
                metadata=V1ObjectMeta(labels=pod.metadata.labels),
                spec=pod.spec
            )
        )
    )
    return deployment


def construct_service(
        name: str,
        namespace: str,
        target_port: int,
        selector: dict,
        port: int = None,
        node_port: int = None,
        port_name: str = None,
        expose_type: str = None,
        protocol: str = "TCP",
        cluster_ip: str = None,
) -> V1Service:
    service = V1Service(
        api_version="v1",
        kind="Service",
        metadata=V1ObjectMeta(name=name, namespace=namespace, labels=selector),
        spec=V1ServiceSpec(
            ports=[
                V1ServicePort(
                    name=port_name, port=port, target_port=target_port, node_port=node_port, protocol=protocol
                )
            ],
            selector=selector,
            cluster_ip=cluster_ip,
            type=expose_type
        )
    )

    return service


def construct_hpa(
        name: str,
        namespace: str,
        target_cpu_utilization: int,
        min_replicas: int,
        max_replicas: int,
        target_api_version: str,
        target_kind: str,
        target_name: str
) -> V1HorizontalPodAutoscaler:
    hpa = V1HorizontalPodAutoscaler(
        api_version="autoscaling/v1",
        kind="HorizontalPodAutoscaler",
        metadata=V1ObjectMeta(name=name, namespace=namespace),
        spec=V1HorizontalPodAutoscalerSpec(
            min_replicas=min_replicas,
            max_replicas=max_replicas,
            scale_target_ref=V1CrossVersionObjectReference(
                api_version=target_api_version,
                kind=target_kind,
                name=target_name
            ),
            target_cpu_utilization_percentage=target_cpu_utilization
        )
    )
    return hpa


def construct_configmap(name: str, namespace: str, data: dict, binary_data=None) -> V1ConfigMap:
    cm = V1ConfigMap(
        api_version="v1",
        metadata=V1ObjectMeta(namespace=namespace, name=name),
        data=data,
        binary_data=binary_data
    )
    return cm


def construct_inference_service(
        inference_service_name: str,
        namespace: str,
        *,
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
        max_batch_latency: int = None,
        predictor_restart_policy: str = None,
        transformer_restart_policy: str = None,
) -> V1beta1InferenceService:
    assert predictor_container is not None or transformer_container is not None, "Specify predictor_container and/or" \
                                                                         " transformer_container"

    if predictor_container:
        predictor_spec = V1beta1PredictorSpec(
            min_replicas=predictor_min_replicas,
            max_replicas=predictor_max_replicas,
            batcher=V1beta1Batcher(max_batch_size, max_batch_latency)
            if (max_batch_size and max_batch_latency) else None,
            containers=[_construct_container(predictor_container)],
            volumes=[_construct_volume(v) for v in predictor_volumes] if predictor_volumes else None,
            restart_policy=predictor_restart_policy
        )
    else:
        predictor_spec = None
    if transformer_container:
        transformer_spec = V1beta1TransformerSpec(
            min_replicas=transformer_min_replicas,
            max_replicas=transformer_max_replicas,
            containers=[_construct_container(transformer_container)],
            volumes=[_construct_volume(v) for v in transformer_volumes] if transformer_volumes else None,
            restart_policy=transformer_restart_policy,
        )
    else:
        transformer_spec = None

    return V1beta1InferenceService(
        api_version=constants.KSERVE_V1BETA1,
        kind=constants.KSERVE_KIND,
        metadata=V1ObjectMeta(name=inference_service_name, namespace=namespace, labels=labels),
        spec=V1beta1InferenceServiceSpec(
            predictor=predictor_spec,
            transformer=transformer_spec
        )
    )
