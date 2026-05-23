# ══════════════════════════════════════════════
#  variables.tf — EmergencyQ
#
#  Ye file kya karti hai?
#  Variables define karti hai — jaise function
#  ke parameters hote hain waise.
#
#  CLEANED UP: RDS bana hua hai pehle se, isliye
#  db_password, db_name, db_username, db_instance_class
#  hata diye. Ab sirf wahi variables hain jo
#  main.tf mein actually USE hote hain.
# ══════════════════════════════════════════════


# ── AWS Region ─────────────────────────────────
variable "aws_region" {
  description = "Kaunse AWS region mein resources banane hain"
  type        = string
  default     = "ap-south-1"     
}


# ── Environment ────────────────────────────────
variable "environment" {
  description = "dev, staging, ya prod — kaunsa environment hai"
  type        = string
  default     = "dev"
}


# ── Project Name ───────────────────────────────
variable "project_name" {
  description = "Project ka naam — resource naming mein use hoga"
  type        = string
  default     = "emergencyq"
}


# ── EC2 Instance Type ─────────────────────────
variable "instance_type" {
  description = "EC2 server ka size (CPU + RAM)"
  type        = string
  default     = "t3.medium"      # 2 vCPU, 4 GB RAM — ML model ke liye minimum
  # t3.micro  = 1 vCPU, 1 GB  (free tier but too small for ML)
  # t3.medium = 2 vCPU, 4 GB  (good for dev/staging)
  # t3.large  = 2 vCPU, 8 GB  (good for production)
}


# ── SSH Key ────────────────────────────────────
# AWS Console → EC2 → Key Pairs mein jo naam diya tha wahi yahan hai
variable "key_pair_name" {
  description = "AWS EC2 mein SSH access ke liye key pair ka naam"
  type        = string
  default     = "emergencyq-key"   # ✅ Tera banaya hua key pair
}
