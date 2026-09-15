terraform {
  backend "s3" {
    # A backend block cannot use variables, so the account-specific bucket name is not
    # written here. It is supplied at init time from backends/local.s3.tfbackend, which
    # is gitignored; the Makefile targets pass both that and the per-environment key.
    key = "sph/terraform.tfstate"
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
