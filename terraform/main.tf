terraform {
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

data "aws_ami" "ubuntu" {
  most_recent = true
  owners = ["099720109477"]
  filter {
    name = "name"
    values = ["ubuntu/images/hvm-ssd-gp3/ubuntu-resolute-26.04-amd64-server-*"]
  }
}

data "aws_key_pair" "SPH_deployer" {
  key_name = "SPH-EC2-deployer-key"
}

data "aws_vpc" "default" {
  default = true
}

data "aws_subnets" "default" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
}

resource "aws_security_group" "SPH_security_group" {
  name = "SPH-EC2-security-group"
  description = "Configure ingress/egress traffic for SpotifyPlaylistHelpers app"
  vpc_id = data.aws_vpc.default.id
}

resource "aws_vpc_security_group_ingress_rule" "allow_ssh_for_maintainer" {
  security_group_id = aws_security_group.SPH_security_group.id
  cidr_ipv4 = var.maintainer_machine_cidr
  ip_protocol = "tcp"
  from_port = "22"
  to_port = "22"
}

resource "aws_vpc_security_group_ingress_rule" "allow_dev_flask_for_maintainer" {
  security_group_id = aws_security_group.SPH_security_group.id
  cidr_ipv4 = var.maintainer_machine_cidr
  ip_protocol = "tcp"
  from_port = "3000"
  to_port = "3000"
}

resource "aws_vpc_security_group_ingress_rule" "allow_http" {
  security_group_id = aws_security_group.SPH_security_group.id
  cidr_ipv4 = "0.0.0.0/0"
  ip_protocol = "tcp"
  from_port = "80"
  to_port = "80"
}

resource "aws_vpc_security_group_ingress_rule" "allow_https" {
  security_group_id = aws_security_group.SPH_security_group.id
  cidr_ipv4 = "0.0.0.0/0"
  ip_protocol = "tcp"
  from_port = "443"
  to_port = "443"
}

resource "aws_vpc_security_group_egress_rule" "allow_all" {
  security_group_id = aws_security_group.SPH_security_group.id
  cidr_ipv4 = "0.0.0.0/0"
  ip_protocol = "-1"
}

resource "aws_instance" "SPH_machine_01" {
  instance_type = "t2.micro"
  tags = {
    Name = "SPH-machine-01"
  }
  ami = data.aws_ami.ubuntu.id
  key_name = data.aws_key_pair.SPH_deployer.key_name
  vpc_security_group_ids = [aws_security_group.SPH_security_group.id]
  subnet_id = sort(data.aws_subnets.default.ids)[0]
  associate_public_ip_address = true
}
