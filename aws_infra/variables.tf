variable "env" {
  type = string
  nullable = false

  validation {
    condition = contains(["dev", "prod"], var.env)
    error_message = "Environment must be dev or prod."
  }
}

variable "region" {
  type = string
  default = "us-east-1"
}

variable "availability_zone" {
  type = string
  default = "us-east-1a"
}

variable "maintainer_machine_cidr" {
  type = string
  nullable = false

  validation {
    condition = can(cidrhost(var.maintainer_machine_cidr, 0))
    error_message = "maintainer_machine_cidr must be a valid CIDR, e.g. 1.2.3.4/32."
  }
}