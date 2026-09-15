data "aws_vpc" "default" {
  default = true
}

data "aws_subnets" "default" {
  for_each = toset(var.availability_zones)

  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }

  filter {
    name   = "availability-zone"
    values = [each.value]
  }
}

locals {
  # One default subnet per configured zone, in the same order as var.availability_zones.
  # sort() keeps the pick stable if a zone ever holds more than one default subnet.
  default_subnet_ids = [
    for az in var.availability_zones : sort(data.aws_subnets.default[az].ids)[0]
  ]
}
