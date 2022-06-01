Kubernetes Python Client
-

> Based-on the official [Kubernetes Python client](https://github.com/kubernetes-client/python)


### Usage
```python
from kube_resources.services import create_service
from kube_resources.configmaps import create_configmap

create_configmap("configmap_name", namespace="default", data={"key": "value"})

create_service(
    "service_name", target_port=8080, namespace="default", expose_type="NodePort", selector={"label": "value"}
)
```
