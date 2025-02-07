import base64
import pulumi
import pulumi_azure_native as azure_native
from pulumi_azure_native import containerservice
import pulumi_azuread as azuread
import pulumi_tls as tls
import pulumi_kubernetes as k8s
import pulumi
from pulumi_kubernetes.apps.v1 import Deployment
from pulumi_kubernetes.core.v1 import Service
from pulumi_kubernetes.networking.v1 import Ingress
from pulumi_kubernetes_ingress_nginx import (
    IngressController,
    ControllerArgs,
    ControllerPublishServiceArgs,
)


cluster_name = "krapdev"
config = pulumi.Config()


# Resource Group
resource_group = azure_native.resources.ResourceGroup(
    f"rg-{cluster_name}", location="uksouth"
)


# Create an AD service principal
ad_app = azuread.Application("aks", display_name="aks")
ad_sp = azuread.ServicePrincipal("aksSp", client_id=ad_app.client_id)

# Create the Service Principal Password
ad_sp_password = azuread.ServicePrincipalPassword(
    "aksSpPassword", service_principal_id=ad_sp.id, end_date="2099-01-01T00:00:00Z"
)

# Generate an SSH key
ssh_key = tls.PrivateKey("ssh-key", algorithm="RSA", rsa_bits=4096)


# Azure Storage Account
storage_account = azure_native.storage.StorageAccount(
    f"st{cluster_name}",
    resource_group_name=resource_group.name,
    location=resource_group.location,
    sku=azure_native.storage.SkuArgs(
        name=azure_native.storage.SkuName.STANDARD_LRS,
    ),
    kind=azure_native.storage.Kind.STORAGE_V2,
)

# Azure Container Registry
container_registry = azure_native.containerregistry.Registry(
    f"acr{cluster_name}",
    resource_group_name=resource_group.name,
    location=resource_group.location,
    sku=azure_native.containerregistry.SkuArgs(
        name="Standard",
    ),
    admin_user_enabled=True,
)

# Managed Identity for AKS
identity = azure_native.managedidentity.UserAssignedIdentity(
    f"id{cluster_name}",
    resource_group_name=resource_group.name,
    location=resource_group.location,
)

# AKS Cluster with Managed Identity
kubernetes_cluster = azure_native.containerservice.ManagedCluster(
    f"aks-{cluster_name}",
    resource_group_name=resource_group.name,
    network_profile=azure_native.containerservice.ContainerServiceNetworkProfileArgs(
        network_plugin="kubenet",
    ),
    location=resource_group.location,
    dns_prefix=f"dns-{cluster_name}",
    agent_pool_profiles=[
        azure_native.containerservice.ManagedClusterAgentPoolProfileArgs(
            name="agentpool",
            count=1,
            vm_size="Standard_DS2_v2",
            os_type="Linux",
            mode="System",
            type="VirtualMachineScaleSets",
        )
    ],
    # identity=azure_native.containerservice.UserAssignedIdentityArgs(identity.client_id),
    # identity=azure_native.containerservice.ManagedClusterIdentityArgs(
    #     type="UserAssigned", user_assigned_identities={identity.id: {}}
    # ),
    service_principal_profile=azure_native.containerservice.ManagedClusterServicePrincipalProfileArgs(
        client_id=ad_app.client_id, secret=ad_sp_password.value
    ),
    linux_profile=azure_native.containerservice.ContainerServiceLinuxProfileArgs(
        admin_username="testuser",
        ssh=azure_native.containerservice.ContainerServiceSshConfigurationArgs(
            public_keys=[
                azure_native.containerservice.ContainerServiceSshPublicKeyArgs(
                    key_data=ssh_key.public_key_openssh,
                )
            ]
        ),
    ),
)


creds = containerservice.list_managed_cluster_user_credentials_output(
    resource_group_name=resource_group.name, resource_name=kubernetes_cluster.name
)
encoded = creds.kubeconfigs[0].value
kubeconfig = encoded.apply(lambda enc: base64.b64decode(enc).decode())
pulumi.export("kubeconfig", kubeconfig)


k8s_provider = k8s.Provider("k8s-provider", kubeconfig=kubeconfig)


###############################################################################
# Install ArgoCD
###############################################################################

# Create a new namespace for ArgoCD
# argocd_namespace = k8s.core.v1.Namespace(
#     resource_name="argocd",
#     metadata={
#         "name": "argocd",
#     },
#     opts=pulumi.ResourceOptions(provider=k8s_provider),
# )


# Use kubectl or python client to install ArgoCD
# This keeps the number of Pulimi resources within the free tier
# kubectl create namespace argocd
# kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml

# Alternatively convert this entire setup to bicep but this will require bootstrapping for state management that
# Pulumu provides out of the box

# # Install the NGINX ingress controller to our cluster. The controller
# # consists of a Pod and a Service. Install it and configure the controller
# # to publish the load balancer IP address on each Ingress so that
# # applications can depend on the IP address of the load balancer if needed.
# nginx = IngressController(
#     "nginx",
#     controller=ControllerArgs(
#         publish_service=ControllerPublishServiceArgs(
#             enabled=True,
#         ),
#     ),
#     opts=pulumi.ResourceOptions(depends_on=kubernetes_cluster, provider=k8s_provider),
# )


# # Next, expose the app using an Ingress.
# argocd_ingress = Ingress(
#     "argocd-ingress",
#     opts=pulumi.ResourceOptions(depends_on=nginx, provider=k8s_provider),
#     metadata={
#         "name": "argocd-ingress",
#         "annotations": {
#             "kubernetes.io/ingress.class": "nginx",
#             "nginx.ingress.kubernetes.io/force-ssl-redirect": "true",
#             "nginx.ingress.kubernetes.io/ssl-passthrough": "true",
#         },
#     },
#     spec={
#         "rules": [
#             {
#                 # Replace this with your own domain!
#                 # "host": "argocd.landertre-dev.org",
#                 "http": {
#                     "paths": [
#                         {
#                             "pathType": "Prefix",
#                             "path": "/",
#                             "backend": {
#                                 "service": {
#                                     "name": "argocd-server",
#                                     "port": {"number": 80},
#                                 },
#                             },
#                         }
#                     ],
#                 },
#             },
#         ],
#     },
# )
