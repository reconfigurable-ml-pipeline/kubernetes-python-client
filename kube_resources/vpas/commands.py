from kube_resources import vpa_api


def _get_vpa_info(vpa: dict):
    return {
        "kind": "VerticalPodAutoscaler",
        "namespace": vpa["metadata"]["namespace"],
        "name": vpa["metadata"]["name"],
        "min_allowed": vpa["spec"]["resourcePolicy"]["containerPolicies"][0]["minAllowed"],
        "max_allowed": vpa["spec"]["resourcePolicy"]["containerPolicies"][0]["maxAllowed"],
        "target": {
            "api_version": vpa["spec"]["targetRef"]["apiVersion"],
            "kind": vpa["spec"]["targetRef"]["kind"],
            "name": vpa["spec"]["targetRef"]["name"],
        },
        "update_mode": vpa["spec"]["updatePolicy"]["updateMode"],
        "status": {
            "recommendation": vpa["status"]["recommendation"]
        } if vpa.get("status") else None
    }
    

def create_vpa(
    name: str,
    target_api_version: str,
    target_kind: str,
    target_name: str,
    target_container_name: str,
    min_allowed: dict = None,
    max_allowed: dict = None,
    controlled_resources: list = None,
    update_mode="Auto",
    namespace="default"
):
    policies = None
    if max_allowed or min_allowed:
        policies = {"containerName": f"{target_container_name}"}
    if max_allowed:
        policies["maxAllowed"] = {}
        if max_allowed.get("cpu"):
            policies["maxAllowed"]["cpu"] = max_allowed["cpu"]
        if max_allowed.get("memory"):
            policies["maxAllowed"]["memory"] = max_allowed["memory"]
    if min_allowed:
        policies["minAllowed"] = {}
        if min_allowed.get("cpu"):
            policies["minAllowed"]["cpu"] = min_allowed["cpu"]
        if min_allowed.get("memory"):
            policies["minAllowed"]["memory"] = min_allowed["memory"]
    if controlled_resources:
        policies["controlledResources"] = controlled_resources
    
    body = {
        "apiVersion": "autoscaling.k8s.io/v1",
        "kind": "VerticalPodAutoscaler",
        "metadata": {
            "name": f"{name}",
            "namespace": f"{namespace}"
        },
        "spec": {
            "targetRef": {
                "apiVersion": f"{target_api_version}",
                "kind": f"{target_kind}",
                "name": f"{target_name}"
            },
            "updatePolicy": {
                "updateMode": f"{update_mode}"
            },
            "resourcePolicy": {
                "containerPolicies": [policies] if policies else []
            }
        }
    }
    path_params = {"namespace": namespace}

    header_params = {'Accept': vpa_api.api_client.select_header_accept(['application/json'])}

    vpa_api.api_client.call_api(
        '/apis/autoscaling.k8s.io/v1/namespaces/{namespace}/verticalpodautoscalers', 'POST',
        path_params,
        None,
        header_params,
        body=body,
        auth_settings=['BearerToken'],
    )
    return get_vpa(name, namespace)
    


def get_vpa(name: str, namespace="default"):
    header_params = {'Accept': vpa_api.api_client.select_header_accept(['application/json'])}
    return _get_vpa_info(vpa_api.api_client.call_api(
        '/apis/autoscaling.k8s.io/v1/namespaces/{namespace}/verticalpodautoscalers/{name}', 'GET',
        {"namespace": namespace, "name": name},
        None,
        header_params,
        response_type="json",
        auth_settings=['BearerToken'],
    )[0])


def delete_vpa(name: str, namespace="default"):
    vpa_api.api_client.call_api(
        '/apis/autoscaling.k8s.io/v1/namespaces/{namespace}/verticalpodautoscalers/{name}', 'DELETE',
        {"namespace": namespace, "name": name},
        query_params=None,
        header_params=None,
        # response_type='V1Status',
        auth_settings=['BearerToken'],
    )