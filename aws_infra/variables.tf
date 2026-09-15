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

variable "availability_zones" {
  type = list(string)
  default = ["us-east-1a", "us-east-1b"]
  nullable = false

  validation {
    condition = length(var.availability_zones) >= 2
    error_message = "At least two availability zones are required, the load balancer needs a subnet in each."
  }

  validation {
    condition = length(distinct(var.availability_zones)) == length(var.availability_zones)
    error_message = "availability_zones must not contain duplicates."
  }
}

variable "instance_type" {
  # t2 rather than a current-generation t3/t4g: this is a new account, where the
  # "Running On-Demand Standard instances" quota is 1 vCPU. That quota counts vCPUs,
  # and the smallest t3 is t3.micro at 2, so t2.micro at 1 is the only fit. Worth
  # revisiting once the quota is raised.
  type = string
  default = "t2.micro"
  nullable = false
}

variable "load_balancer_log_retention_days" {
  type = number
  default = 7
  nullable = false

  validation {
    condition = var.load_balancer_log_retention_days >= 1
    error_message = "load_balancer_log_retention_days must be at least 1."
  }
}

variable "maintainer_machine_cidr" {
  type = string
  nullable = false

  validation {
    condition = can(cidrhost(var.maintainer_machine_cidr, 0))
    error_message = "maintainer_machine_cidr must be a valid CIDR, e.g. 1.2.3.4/32."
  }
}