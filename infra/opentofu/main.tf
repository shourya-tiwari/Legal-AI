# OpenTofu module (docs/v2/ROADMAP.md Phase 7 "Build & supply chain" --
# "OpenTofu for all IaC; migrate off any Terraform"). Neither `terraform`
# nor `tofu` is installed in this environment, so `tofu validate`/`tofu
# plan` have not been run against this file -- written carefully against
# OpenTofu 1.x's documented HCL syntax, but that's the one part of this
# item genuinely unverified here (see docs/v2/TASKS.md).
#
# Deliberately thin: it does not re-model every Kubernetes resource as a
# first-class OpenTofu resource (that would duplicate, and inevitably
# drift from, deploy/kustomize/ and deploy/helm/legalai/ -- both already
# hand-validated where the tooling exists to do so: `kubectl kustomize`
# for the overlays, nothing for the Helm chart). Instead this module is the
# orchestration layer: it applies whichever already-validated manifest set
# the target profile calls for. IaC's job here is "which cluster, which
# profile, which secrets," not "reinvent the manifests in a second syntax."

terraform {
  required_version = ">= 1.6.0"
  required_providers {
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.31"
    }
  }
}

variable "kubeconfig_path" {
  description = "Path to the target cluster's kubeconfig. Empty string = in-cluster config (e.g. running this from a CI runner with a service account)."
  type        = string
  default     = "~/.kube/config"
}

variable "profile" {
  description = "Which Kustomize overlay to apply: on-prem | cloud | gpu."
  type        = string
  default     = "on-prem"
  validation {
    condition     = contains(["on-prem", "cloud", "gpu"], var.profile)
    error_message = "profile must be one of: on-prem, cloud, gpu."
  }
}

variable "namespace" {
  description = "Kubernetes namespace to deploy into. Must match deploy/kustomize's hardcoded 'legalai' namespace unless the overlays are also repointed."
  type        = string
  default     = "legalai"
}

provider "kubernetes" {
  config_path = var.kubeconfig_path
}

resource "kubernetes_namespace" "legalai" {
  metadata {
    name = var.namespace
  }
}

# `kubectl apply -k` is the one command that actually understands a
# Kustomize overlay tree the way `kubectl kustomize` (used to hand-validate
# every overlay in this repo) already proved renders correctly -- reaching
# for the community kubectl provider or hand-porting every resource into
# `kubernetes_manifest` blocks would either add an unverified third-party
# provider or duplicate deploy/kustomize/ a second time. A `local-exec`
# provisioner needs `kubectl` on whatever machine runs `tofu apply`, which
# every profile here already assumes.
resource "null_resource" "apply_overlay" {
  depends_on = [kubernetes_namespace.legalai]

  triggers = {
    profile = var.profile
  }

  provisioner "local-exec" {
    command = "kubectl --kubeconfig='${var.kubeconfig_path}' apply -k '${path.module}/../../deploy/kustomize/overlays/${var.profile}'"
  }
}
