resource "aws_security_group" "application_machine" {
  name = "sph-${var.env}-application-machine"
  description = "Configure ingress/egress traffic for SpotifyPlaylistHelpers application host"
  vpc_id = data.aws_vpc.default.id
}

resource "aws_vpc_security_group_ingress_rule" "allow_ssh_for_maintainer" {
  security_group_id = aws_security_group.application_machine.id
  cidr_ipv4 = var.maintainer_machine_cidr
  ip_protocol = "tcp"
  from_port = "22"
  to_port = "22"
}

resource "aws_vpc_security_group_ingress_rule" "allow_dev_flask_for_maintainer" {
  count = var.env == "dev" ? 1 : 0

  security_group_id = aws_security_group.application_machine.id
  cidr_ipv4 = var.maintainer_machine_cidr
  ip_protocol = "tcp"
  from_port = "3000"
  to_port = "3000"
}

resource "aws_vpc_security_group_ingress_rule" "allow_http" {
  security_group_id = aws_security_group.application_machine.id
  cidr_ipv4 = "0.0.0.0/0"
  ip_protocol = "tcp"
  from_port = "80"
  to_port = "80"
}

resource "aws_vpc_security_group_ingress_rule" "allow_https" {
  security_group_id = aws_security_group.application_machine.id
  cidr_ipv4 = "0.0.0.0/0"
  ip_protocol = "tcp"
  from_port = "443"
  to_port = "443"
}

resource "aws_vpc_security_group_egress_rule" "allow_all" {
  security_group_id = aws_security_group.application_machine.id
  cidr_ipv4 = "0.0.0.0/0"
  ip_protocol = "-1"
}
