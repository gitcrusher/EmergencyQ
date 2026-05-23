# ══════════════════════════════════════════════
#  outputs.tf — EmergencyQ
#
#  Ye file kya karti hai?
#  Jab `terraform apply` complete ho jaata hai,
#  ye file batati hai: "Ye banaya hai, ye hai uska address"
#
#  Jaise Amazon order ke baad tracking number milta hai,
#  waise terraform apply ke baad ye outputs milte hain:
#    → Server ka IP address
#    → Database ka endpoint
#    → S3 bucket ka naam
#
#  In values ko tu apni .env file mein daal sakta hai
#  ya Jenkins pipeline mein use kar sakta hai.
# ══════════════════════════════════════════════


# ── EC2 Server IP ──────────────────────────────
output "server_public_ip" {
  description = "EC2 server ka persistent public IP (Elastic IP) — browser mein ye daalo"
  value       = aws_eip.app_eip.public_ip
}

output "server_public_dns" {
  description = "EC2 server ka persistent DNS name"
  value       = aws_eip.app_eip.public_dns
}


# ────────────────────────────────────────────
# ❌ RDS OUTPUTS — SKIP (RDS already bana hua hai)
# DATABASE_URL already .env mein hai:
#   postgresql://postgres:Aayushsoni05@database-1.czu8eyogcrsm...
# ────────────────────────────────────────────

# output "database_endpoint" {
#   description = "PostgreSQL ka endpoint"
#   value       = aws_db_instance.postgres.endpoint
# }

# output "database_url" {
#   description = "Full DATABASE_URL"
#   value       = "postgresql://${var.db_username}:PASSWORD@${aws_db_instance.postgres.endpoint}/${var.db_name}"
#   sensitive   = true
# }


# ── S3 Bucket ──────────────────────────────────
output "model_bucket_name" {
  description = "S3 bucket ka naam — ML model files yahan upload karo"
  value       = aws_s3_bucket.model_artifacts.bucket
}


# ── SSH Command ────────────────────────────────
output "ssh_command" {
  description = "Server pe SSH se connect karne ka command"
  value       = "ssh -i ${var.key_pair_name}.pem ubuntu@${aws_eip.app_eip.public_ip}"
}
