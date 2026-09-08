variable "region" {
  type = string
  default = "us-east-1"
}

variable "maintainer_machine_cidr" {
  type = string
  nullable = false

  validation {
    condition = can(cidrhost(var.maintainer_machine_cidr, 0))
    error_message = "maintainer_machine_cidr must be a valid CIDR, e.g. 1.2.3.4/32."
  }
}