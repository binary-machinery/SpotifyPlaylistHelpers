SpotifyPlaylistHelpers
======================

A small Flask app with helper tools for managing Spotify playlists.

This is an older app that I created in 2022 to organize my Spotify library. It's not in a production-ready quality,
I used to run it locally with ngrok when I needed it, it was for personal use only. I'm currently improving it with 
modern backend practices and technologies.


Features
--------------

- **New releases for a playlist** — for every artist in the playlist, finds the most recent release date among that
  playlist's tracks, then lists the albums and singles that artist has put out since. A way to catch up on artists you
  already listen to.
- **Add an artist to a playlist** — appends every track from an artist's albums and singles to a playlist, oldest
  release first.
- **Subtract a playlist from a playlist** — removes from one playlist every track that appears in another.
- **DeLivery: filter out a keyword** — gathers the tracks whose title contains a keyword (`live`, `instrumental`,
  `inst.`, `remix`) into a new private playlist named `delivery-<keyword>-<playlist>`. Once you have reviewed it, use
  "Subtract a playlist from a playlist" to remove those tracks from the original.
- **DeLivery: filter out duplicates** — the same, for tracks that look like duplicates of each other (same title, same
  artists), gathering the earlier-released copy of each pair. Currently broken, see `TODO.md`.

Signing in goes through Spotify's OAuth authorization code flow; the app requests the `playlist-read-private`,
`playlist-modify-private` and `playlist-modify-public` scopes.


Roadmap
--------------

- [**In Progress**] Configure AWS infrastructure
- [**In Progress**] Configure CI/CD with GitHub Actions
- [**TODO**] Fix "DeLivery: filter out duplicates"
- [**TODO**] Use Poetry
- [**TODO**] Add semantic versioning
- [**TODO**] Rewrite with FastAPI
- [**TODO**] Rewrite in Go
- [**TODO**] Rewrite in Rust


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
