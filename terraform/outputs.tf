
#  when `terraform apply` complete then it gives output
#    → Server IP address
#    → S3 bucket ka naam
#  


# EC2 server IP
output "server_public_ip" {
  description = "EC2 server's persistent public IP (Elastic IP) "
  value       = aws_eip.app_eip.public_ip
}

output "server_public_dns" {
  description = "EC2 server's persistent DNS name"
  value       = aws_eip.app_eip.public_dns
}




# S3 Bucket 
output "model_bucket_name" {
  description = "S3 bucket's name"
  value       = aws_s3_bucket.model_artifacts.bucket
}


# SSH Command 
output "ssh_command" {
  description = "SSH connect command"
  value       = "ssh -i ${var.key_pair_name}.pem ubuntu@${aws_eip.app_eip.public_ip}"
}
