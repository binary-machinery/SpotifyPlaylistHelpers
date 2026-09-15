# Multiple -backend-config flags are merged, so the gitignored bucket file and the
# committed per-environment key file together make up the full backend configuration.
terraform-init-dev:
	terraform init -reconfigure -input=false \
	  -backend-config=backends/local.s3.tfbackend \
	  -backend-config=backends/dev.s3.tfbackend

terraform-init-prod:
	terraform init -reconfigure -input=false \
	  -backend-config=backends/local.s3.tfbackend \
	  -backend-config=backends/prod.s3.tfbackend
