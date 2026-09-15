terraform {
  backend "s3" {
    # Deliberately partial: nothing naming or locating the state is written here, so an
    # "init" with the wrong flags has no default to quietly fall back on. The bucket and
    # the region it lives in come from backends/local.s3.tfbackend (gitignored, specific
    # to whoever is deploying) and the state key from backends/<env>.s3.tfbackend; the
    # Makefile targets pass both. Only the two settings below hold for every deployment.
    use_lockfile = true
    encrypt = true
  }

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }

  required_version = ">= 1.10.0"
}

provider "aws" {
  region = var.region

  default_tags {
    tags = {
      Project = "spotify-playlist-helpers"
      Environment = var.env
      ManagedBy = "terraform"
    }
  }
}
