terraform {
  backend "s3" {
    # Deliberately partial: neither the bucket nor the state key is written here, so
    # there is no default state for an "init" with the wrong flags to fall back on.
    # The bucket comes from backends/local.s3.tfbackend (gitignored, account-specific)
    # and the key from backends/<env>.s3.tfbackend; the Makefile targets pass both.
    region = "us-east-1"
    use_lockfile = true
    encrypt = true
  }

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }

  required_version = ">= 1.5.0"
}

provider "aws" {
  region = var.region
}
