SpotifyPlaylistHelpers
======================

A small Flask app with helper tools for managing Spotify playlists.

This is an older app that I created in 2022 to organize my Spotify library. It's not in a production-ready quality,
I used to run it in dev mode locally with ngrok when I needed it, it was for personal use only. I'm currently improving 
it with modern backend practices and technologies for infrastructure and deployment.


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
- [**In Progress**] Use Poetry
- [**In Progress**] Add semantic versioning
- [**In Progress**] Rewrite with FastAPI
- [**TODO**] Configure CI/CD with GitHub Actions
- [**TODO**] Fix "DeLivery: filter out duplicates"
- [**TODO**] Rewrite in Go
- [**TODO**] Rewrite in Rust


Configuration
--------------

The app reads its settings from `configs/config.json` on startup (`config_loader.py`). That file is gitignored because
it carries the Spotify credentials; `configs/config_template.json` is the committed shape of it:

```json
{
  "server": {
    "port": 3000,
    "secret_key": "${FLASK_SECRET_KEY}",
    "host": "${SERVER_HOST}"
  },
  "spotify": {
    "client_id": "${SPOTIFY_CLIENT_ID}",
    "client_secret": "${SPOTIFY_CLIENT_SECRET}"
  }
}
```

- `server.port` — the port Flask listens on. `3000` everywhere: both compose files publish it and the load balancer
  target group health-checks it.
- `server.secret_key` — Flask session signing key. Any long random string.
- `server.host` — the public origin the app is reached at, with scheme and no trailing slash. The Spotify redirect URI
  is built from it as `<host>/auth-callback`. Spotify supports `http://127.0.0.1` for local development.
- `spotify.client_id`, `spotify.client_secret` — credentials of an app registered in the Spotify developer dashboard.

### Running locally

Register an application at https://developer.spotify.com/dashboard, then copy the template and fill in the values:

```sh
cp configs/config_template.json configs/config.json
```
Spotify will not redirect to an arbitrary address, so `server.host` has to be an origin it accepts and that reaches
your machine. No need for ngrok anymore, Spotify supports `http://127.0.0.1` for local development, but the redirect URI
must be configured in the app settings in the Spotify dev dashboard. For an actual host, HTTPS is required. 

Then:

```sh
docker compose up --build
```

`compose.yaml` mounts `configs/config.json` into the container read-only, so the file never ends up in the image.

App is running at http://127.0.0.1:3000.

### On the deployed host

The `${...}` placeholders name SSM parameters under `/sph/<env>/`. `SERVER_HOST` is created by Terraform
(`aws_infra/ssm.tf`) and points at the load balancer's DNS name. `FLASK_SECRET_KEY`, `SPOTIFY_CLIENT_ID` and
`SPOTIFY_CLIENT_SECRET` are SecureStrings added by hand, deliberately outside Terraform so they stay out of the state
file.

Rendering the template into `config.json` on the instance is not automated yet — it is part of the in-progress CI/CD
work, and for now the file is placed on the host manually next to `compose.prod.yaml`.

`compose.prod.yaml` also expects a `.env` file beside it, holding the image to pull. Copy `.env.example` and fill in
the repository URL from the Terraform output:

```sh
cp .env.example .env
cd aws_infra && terraform output -raw ecr_repository_url
```


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

Only locking and encryption — the settings that hold for anyone deploying this
— live in the `backend "s3"` block in `main.tf`. The state key comes from the
per-environment file, and the bucket and its region from a gitignored local
file (see below), so the block names no state of its own: an `init` without the
right `-backend-config` flags fails instead of quietly picking a default.

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

### Local files

Two files under `aws_infra/` are gitignored and have to be created locally,
because they name account-specific things that are kept out of the repository.

`local.auto.tfvars` carries `maintainer_machine_cidr`, the CIDR allowed to SSH
into the application host. The variable has no default, so Terraform prompts
for it otherwise:

```hcl
maintainer_machine_cidr = "1.2.3.4/32"
```

`backends/local.s3.tfbackend` carries the S3 bucket holding the remote state
and the region that bucket lives in:

```hcl
bucket = "terraform-state-<account-id>-<region>-<suffix>"
region = "us-east-1"
```

This one is separate from the committed `backends/<env>.s3.tfbackend` files
because a `backend` block cannot use variables — the bucket cannot be derived
from `var`, so it is supplied at init time instead. The `make terraform-init-*`
targets pass this file and the per-environment key file together, and Terraform
merges the two into one backend configuration.

### Prerequisites

- An S3 bucket for the Terraform state must already exist before the first
  `init`; nothing here creates it. Put its name and region in
  `backends/local.s3.tfbackend`, as described above.

- An EC2 key pair named `sph-<env>-maintainer-key` must already exist in the
  region; Terraform looks it up as a data source rather than creating it.


License
--------------

MIT, see [LICENSE](LICENSE).
