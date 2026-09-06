{{- define "legalai.fullname" -}}
legalai
{{- end -}}

{{- define "legalai.labels" -}}
app.kubernetes.io/name: {{ include "legalai.fullname" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end -}}
