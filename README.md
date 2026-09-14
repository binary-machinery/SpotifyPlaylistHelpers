SpotifyPlaylistHelpers
======================

A small Flask app with helper tools for managing Spotify playlists.


Infrastructure
--------------

The AWS infrastructure lives in `aws_infra/` and is managed with Terraform.

### Environments and state

There are two environments, `dev` and `prod`. They share the same Terraform
configuration but keep **separate remote states** in the same S3 bucket, each
under its own key:

| Env    | Backend config                     | State key                  |
|--------|------------------------------------|----------------------------|
| `dev`  | `backends/dev.s3.tfbackend`        | `sph-dev/terraform.tfstate`  |
| `prod` | `backends/prod.s3.tfbackend`       | `sph-prod/terraform.tfstate` |

The bucket, region, locking and encryption settings are shared and live in the
`backend "s3"` block in `main.tf`; the per-environment files only override the
state key.

Resource names are suffixed with the environment as well (`sph-dev-*`,
`sph-prod-*`), driven by the `env` variable.

### Switching environments

`aws_infra/Makefile` has a preset per environment that reconfigures Terraform
to point at the matching backend. Run them from `aws_infra/`:

```sh
make terraform-init-dev     # terraform init -reconfigure ... -backend-config=backends/dev.s3.tfbackend
make terraform-init-prod    # terraform init -reconfigure ... -backend-config=backends/prod.s3.tfbackend
```

`-reconfigure` makes Terraform drop the previously initialised backend instead
of offering to migrate state between the two environments.

After initialising, `plan` and `apply` work against the selected state. The
`env` variable has no default and must be passed on every run — Terraform
prompts for it otherwise:

```sh
make terraform-init-dev
terraform plan -var env=dev
terraform apply -var env=dev
```

```sh
make terraform-init-prod
terraform plan -var env=prod
terraform apply -var env=prod
```

Keep the two in sync: `env` selects the resource names, the backend selects the
state they are recorded in, so a mismatch would write one environment's
resources into the other's state. And whenever you switch environments, re-run
the corresponding `make terraform-init-*` target first — otherwise `plan` and
`apply` keep using the backend from the last `init`.

### Local variables

`maintainer_machine_cidr` (the CIDR allowed to SSH into the application host)
has no default either. It is read from `aws_infra/local.auto.tfvars`, which is
gitignored and has to be created locally:

```hcl
maintainer_machine_cidr = "1.2.3.4/32"
```

### Prerequisites

- An EC2 key pair named `sph-<env>-maintainer-key` must already exist in the
  region; Terraform looks it up as a data source rather than creating it.
