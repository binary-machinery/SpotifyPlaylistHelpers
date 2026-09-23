SpotifyPlaylistHelpers
======================

A small FastAPI app with helper tools for managing Spotify playlists.

This is an older app that I created in 2022 using Flask to organize my Spotify library. It's not in a production-ready
quality, I used to run it in dev mode locally with ngrok when I needed it, it was for personal use only. I'm currently
improving it with modern backend practices and technologies for infrastructure and deployment.


Features
--------------

The app is a JSON API with no UI of its own. Every playlist endpoint acts on behalf of the signed-in Spotify user.

### New releases for a playlist

`GET /playlists/{playlist_id}/new-releases`

For every artist in the playlist, finds the most recent release date among that playlist's tracks, then lists the
albums and singles that artist has put out since. A way to catch up on artists you already listen to.

### Add an artist to a playlist

`POST /playlists/{playlist_id}/add-artist?artist_id=...`

Appends every track from an artist's albums and singles to a playlist, oldest release first.

### Subtract a playlist from a playlist

`POST /playlists/{playlist_id}/subtract-playlist?target_playlist_id=...`

Removes from one playlist every track that appears in another.

### Extract tracks by keyword

`POST /playlists/{playlist_id}/extract-tracks?keyword=...`

Gathers the tracks whose title contains a keyword (case-insensitive, e.g. `live`, `instrumental`, `remix`) into a new
private playlist named `delivery-<keyword>-<playlist>`, or into an existing one passed as `result_playlist_id`. Once you
have reviewed it, use "Subtract a playlist from a playlist" to remove those tracks from the original.

### Extract duplicates

`POST /playlists/{playlist_id}/extract-duplicates`

The same, for tracks that look like duplicates of each other (same title, same artists), gathering the earlier-released
copy of each pair into `delivery-duplicates-<playlist>`, or into `result_playlist_id`. Currently broken: the artist
comparison is a no-op, so tracks sharing a title and artist count are flagged regardless of the actual artists.

### Other endpoints

- `GET /playlists` — the current user's playlists.
- `GET /auth` — redirects to Spotify's consent screen.
- `GET /auth-callback` — where Spotify sends the user back after sign-in.
- `GET /me` — the signed-in Spotify user.
- `POST /logout` — clears the session and forgets the stored tokens.
- `GET /health` — liveness check, used by the load balancer.

FastAPI serves interactive docs at `/docs`.

### Signing in

Signing in goes through Spotify's OAuth authorization code flow (with a `state` check); the app requests the
`playlist-read-private`, `playlist-modify-private` and `playlist-modify-public` scopes. The user's Spotify id is kept in
a signed session cookie, and their access and refresh tokens in a SQLite database (`users.sqlite`). Open `/auth` in a
browser to sign in; afterwards `/docs` in the same browser carries the session cookie, so the endpoints can be tried
from there.

### Errors

Spotify errors are mapped to API responses: an auth failure becomes `401`, a rate limit `429` (with `Retry-After` when
Spotify sent one), a Spotify `5xx` becomes `502`.


Roadmap
--------------

- [**Done**] Use Poetry
- [**Done**] Rewrite with FastAPI
- [**In Progress**] Configure AWS infrastructure
- [**TODO**] Configure CI/CD with GitHub Actions
- [**TODO**] Fix "extract duplicates"
- [**TODO**] Rewrite in Go
- [**TODO**] Rewrite in Rust


Configuration
--------------

Settings are loaded with `pydantic-settings` (`sph_backend/settings.py`) from environment variables and from a
`settings.env` file in the working directory; environment variables win. `settings.env` is gitignored because it
carries the Spotify credentials; `settings.env.example` is the committed shape of it:

```sh
# required parameters
SERVER_HOST=http://127.0.0.1:8000
SERVER_SECRET=...
SPOTIFY_CLIENT_ID=...
SPOTIFY_CLIENT_SECRET=...

# these have default values but can be overridden
USERS_DB_PATH=users.sqlite
AUTH_REDIRECT_ENDPOINT=/auth-callback
```

- `SERVER_HOST` — the public origin the app is reached at, with scheme and no trailing slash. The Spotify redirect URI
  is built from it as `<SERVER_HOST><AUTH_REDIRECT_ENDPOINT>`.
- `SERVER_SECRET` — session cookie signing key. Any long random string.
- `SPOTIFY_CLIENT_ID`, `SPOTIFY_CLIENT_SECRET` — credentials of an app registered in the Spotify developer dashboard.
- `USERS_DB_PATH` — path of the SQLite file holding users' tokens. Created on startup if missing.
- `AUTH_REDIRECT_ENDPOINT` — path of the OAuth callback. Only change it together with the route.

The app listens on port `8000`.

### Running locally

Register an application at https://developer.spotify.com/dashboard, then copy the example and fill in the values:

```sh
cp settings.env.example settings.env
```

Spotify will not redirect to an arbitrary address, so `SERVER_HOST` has to be an origin it accepts and that reaches
your machine. Spotify supports `http://127.0.0.1` for local development; the redirect URI
(`http://127.0.0.1:8000/auth-callback`) must be configured in the app settings in the Spotify dev dashboard. For an
actual host, HTTPS is required.

Then, with Docker:

```sh
docker compose up --build
```

`compose.yaml` mounts `settings.env` into the container read-only, so the file never ends up in the image, and keeps
the users database in the `data` volume.

Or directly, with Python 3.13 and Poetry:

```sh
poetry install
poetry run uvicorn sph_backend.main:app --reload
```

App is running at http://127.0.0.1:8000. Sign in at http://127.0.0.1:8000/auth.

### Tests

```sh
poetry run pytest
```

### On the deployed host

Deployment is a work in progress. `compose.prod.yaml` pulls the image from ECR and expects a `.env` file beside it
naming the image. Copy `.env.example` and fill in the repository URL from the Terraform output:

```sh
cp .env.example .env
cd aws_infra && terraform output -raw ecr_repository_url
```

The app settings are meant to come from SSM parameters under `/sph/<env>/`, named like the variables above.
`SERVER_HOST` is created by Terraform (`aws_infra/ssm.tf`) and points at the load balancer's DNS name. `SERVER_SECRET`,
`SPOTIFY_CLIENT_ID` and `SPOTIFY_CLIENT_SECRET` are SecureStrings added by hand, deliberately outside Terraform so they
stay out of the state file. Passing them into the container is not wired up yet — it is part of the in-progress CI/CD
work.


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
