resource "aws_security_group" "application_machine" {
  name        = "sph-${var.env}-application-machine"
  description = "Configure ingress/egress traffic for SpotifyPlaylistHelpers application host"
  vpc_id      = data.aws_vpc.default.id

  tags = {
    Name = "sph-${var.env}-application-machine"
  }
}

resource "aws_vpc_security_group_ingress_rule" "application_ssh_from_maintainer" {
  description       = "SSH from maintainer workstation"
  security_group_id = aws_security_group.application_machine.id
  cidr_ipv4         = var.maintainer_machine_cidr
  ip_protocol       = "tcp"
  from_port         = "22"
  to_port           = "22"

  tags = {
    Name = "sph-${var.env}-application-ssh-from-maintainer"
  }
}

resource "aws_vpc_security_group_ingress_rule" "application_dev_flask_from_maintainer" {
  count = var.env == "dev" ? 1 : 0

  description       = "Flask development server from maintainer workstation"
  security_group_id = aws_security_group.application_machine.id
  cidr_ipv4         = var.maintainer_machine_cidr
  ip_protocol       = "tcp"
  from_port         = "8000"
  to_port           = "8000"

  tags = {
    Name = "sph-${var.env}-application-flask-from-maintainer"
  }
}

resource "aws_vpc_security_group_ingress_rule" "application_http_from_load_balancer" {
  description                  = "Application traffic and health checks from load balancer"
  security_group_id            = aws_security_group.application_machine.id
  referenced_security_group_id = aws_security_group.load_balancer.id
  ip_protocol                  = "tcp"
  from_port                    = "8000"
  to_port                      = "8000"

  tags = {
    Name = "sph-${var.env}-application-http-from-load-balancer"
  }
}

resource "aws_vpc_security_group_egress_rule" "application_all" {
  description       = "All outbound traffic"
  security_group_id = aws_security_group.application_machine.id
  cidr_ipv4         = "0.0.0.0/0"
  ip_protocol       = "-1"

  tags = {
    Name = "sph-${var.env}-application-all-outbound"
  }
}



resource "aws_security_group" "load_balancer" {
  name        = "sph-${var.env}-load-balancer"
  description = "Configure ingress/egress traffic for SpotifyPlaylistHelpers load balancer"
  vpc_id      = data.aws_vpc.default.id

  tags = {
    Name = "sph-${var.env}-load-balancer"
  }
}

resource "aws_vpc_security_group_ingress_rule" "load_balancer_http" {
  description       = "HTTP from the internet"
  security_group_id = aws_security_group.load_balancer.id
  cidr_ipv4         = "0.0.0.0/0"
  ip_protocol       = "tcp"
  from_port         = "80"
  to_port           = "80"

  tags = {
    Name = "sph-${var.env}-load-balancer-http-from-internet"
  }
}

# TODO: uncomment after LB has a cert
# resource "aws_vpc_security_group_ingress_rule" "load_balancer_https" {
#   description = "HTTPS from the internet"
#   security_group_id = aws_security_group.load_balancer.id
#   cidr_ipv4 = "0.0.0.0/0"
#   ip_protocol = "tcp"
#   from_port = "443"
#   to_port = "443"
# }

resource "aws_vpc_security_group_egress_rule" "load_balancer_http_to_application" {
  description                  = "Application traffic and health checks to application machine"
  security_group_id            = aws_security_group.load_balancer.id
  referenced_security_group_id = aws_security_group.application_machine.id
  ip_protocol                  = "tcp"
  from_port                    = "8000"
  to_port                      = "8000"

  tags = {
    Name = "sph-${var.env}-load-balancer-http-to-application"
  }
}
