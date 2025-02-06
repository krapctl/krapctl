import pulumi
import pulumi_azure_native as azure_native

# Resource Group
resource_group = azure_native.resources.ResourceGroup("resourceGroup")

# Azure Storage Account
storage_account = azure_native.storage.StorageAccount("storageAccount",
    resource_group_name=resource_group.name,
    location=resource_group.location,
    sku=azure_native.storage.SkuArgs(
        name=azure_native.storage.SkuName.STANDARD_LRS,
    ),
    kind=azure_native.storage.Kind.STORAGE_V2)

# Azure Container Registry
container_registry = azure_native.containerregistry.Registry("containerRegistry",
    resource_group_name=resource_group.name,
    location=resource_group.location,
    sku=azure_native.containerregistry.SkuArgs(
        name="Standard",
    ),
    admin_user_enabled=True)

# Managed Identity for AKS
identity = azure_native.managedidentity.UserAssignedIdentity("identity",
    resource_group_name=resource_group.name,
    location=resource_group.location)

# AKS Cluster with Managed Identity
kubernetes_cluster = azure_native.containerservice.ManagedCluster("kubernetesCluster",
    resource_group_name=resource_group.name,
    location=resource_group.location,
    dns_prefix="k8s",
    agent_pool_profiles=[azure_native.containerservice.ManagedClusterAgentPoolProfileArgs(
        name="agentpool",
        count=1,
        vm_size="Standard_DS2_v2",
        os_type="Linux"
    )],
    identity=azure_native.containerservice.ManagedClusterIdentityArgs(
        type="UserAssigned",
        user_assigned_identities={identity.id: {}}
    ),
    service_principal_profile=azure_native.containerservice.ManagedClusterServicePrincipalProfileArgs(
        client_id="your-client-id",
        secret="your-client-secret"
    ),
    linux_profile=azure_native.containerservice.ContainerServiceLinuxProfileArgs(
        admin_username="testuser",
        ssh=azure_native.containerservice.ContainerServiceSshConfigurationArgs(
            public_keys=[azure_native.containerservice.ContainerServiceSshPublicKeyArgs(
                key_data="ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQCy1+zBRhr+3L1dHrqFYeyLLAAvv5N+WKLTCXYTE9TcMeP4wCe5cwPzuy5vj1giZdbnGs2NMRwk1qq4yc8FOB5MgIjXLo7bZGGLi/J3idduIDcyZ+8b8X8Q2mPGeJWin1+XlENeCKVoYQTyZ4yPMBNJQyAQpyBVKD0ghXbQwOzTiDQp5JZEOh5xydAs7yT8//ZeQX2ZOfaCovSu771q5SDE58kSud13GLPcariS5OSZkIgMCFd57QJBP5Ma2K4Gx/JcW4GYcUvXvcFftbvO2n/jXFkTw0OndHZTxXS3JGAkR6Mg12pD3iA6H9QcJuTQ== user@test"
            )]
        )
    ))

# Export the kubeconfig and registry credentials
pulumi.export("kubeconfig", kubernetes_cluster.kube_configs[0].value)
pulumi.export("registry_login_server", container_registry.login_server)
pulumi.export("registry_admin_username", container_registry.admin_user_enabled.username)
pulumi.export("registry_admin_password", container_registry.admin_user_enabled.password)