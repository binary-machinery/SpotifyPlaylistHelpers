output "application_machine_public_ip" {
  value = aws_instance.application_machine.public_ip
}

output "application_machine_public_dns" {
  value = aws_instance.application_machine.public_dns
}
