output "SPH_host_public_ip" {
  value = aws_instance.SPH_machine_01.public_ip
}

output "SPH_host_public_dns" {
  value = aws_instance.SPH_machine_01.public_dns
}
