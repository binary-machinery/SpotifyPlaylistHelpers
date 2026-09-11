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
