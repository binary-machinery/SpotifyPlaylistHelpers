data "aws_ami" "ubuntu" {
  most_recent = true
  owners = ["099720109477"]
  filter {
    name = "name"
    values = ["ubuntu/images/hvm-ssd-gp3/ubuntu-resolute-26.04-amd64-server-*"]
  }
}

data "aws_key_pair" "maintainer" {
  key_name = "sph-${var.env}-maintainer-key"
}

resource "aws_instance" "application_machine" {
  instance_type = "t2.micro"
  tags = {
    Name = "sph-${var.env}-application-machine-01"
  }
  iam_instance_profile = aws_iam_instance_profile.application.name
  ami = data.aws_ami.ubuntu.id
  key_name = data.aws_key_pair.maintainer.key_name
  vpc_security_group_ids = [aws_security_group.application_machine.id]
  subnet_id = local.default_subnet_ids[0]
  associate_public_ip_address = true
  user_data = file("${path.module}/scripts/application_machine_provisioning.sh")
  user_data_replace_on_change = true
}



resource "aws_lb_target_group" "application" {
  name     = "sph-${var.env}-application"
  vpc_id   = data.aws_vpc.default.id
  protocol = "HTTP"
  port     = 3000

  health_check {
    path = "/health"
    matcher = "200"
    interval = 30
    healthy_threshold = 2
    unhealthy_threshold = 2
  }
}

resource "aws_lb_target_group_attachment" "application_machine" {
  target_group_arn = aws_lb_target_group.application.arn
  target_id = aws_instance.application_machine.id
}

resource "aws_s3_bucket" "load_balancer_logs" {
  bucket = "sph-${var.env}-lb-logs"
}

resource "aws_lb" "application" {
  name               = "sph-${var.env}-application"
  internal           = false
  load_balancer_type = "application"

  security_groups = [aws_security_group.load_balancer.id]
  subnets = local.default_subnet_ids

  access_logs {
    bucket  = aws_s3_bucket.load_balancer_logs.id
    prefix  = "lb-${var.env}-logs"
    enabled = true
  }
}

resource "aws_lb_listener" "application" {
  load_balancer_arn = aws_lb.application.arn
  protocol          = "HTTP"
  port              = "80"

  default_action {
    type = "forward"
    target_group_arn = aws_lb_target_group.application.arn
  }
}
