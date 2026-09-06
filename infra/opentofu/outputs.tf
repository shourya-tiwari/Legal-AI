output "namespace" {
  description = "The Kubernetes namespace the overlay was applied into."
  value       = kubernetes_namespace.legalai.metadata[0].name
}

output "profile" {
  value = var.profile
}
