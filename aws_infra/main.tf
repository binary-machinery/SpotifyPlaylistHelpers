terraform {
  backend "s3" {
    bucket = "terraform-state-000000000000-us-east-1-an"
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
