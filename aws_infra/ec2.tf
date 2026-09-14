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
  subnet_id = sort(data.aws_subnets.default.ids)[0]
  associate_public_ip_address = true
  user_data = file("${path.module}/scripts/application_machine_provisioning.sh")
  user_data_replace_on_change = true
}
