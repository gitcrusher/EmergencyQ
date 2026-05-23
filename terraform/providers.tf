# ══════════════════════════════════════════════
#  providers.tf — EmergencyQ
#
#  Ye file kya karti hai?
#  Terraform ko batati hai: "AWS use karna hai"
#
#  Provider = Cloud company jisse baat karni hai
#  Jaise tere phone mein SIM card hoti hai
#  (Jio, Airtel) — waise Terraform mein provider
#  hota hai (AWS, GCP, Azure)
#
#  Ye file SIRF connection setup karti hai.
#  Actual resources (servers, DB) main.tf mein hain.
# ══════════════════════════════════════════════


# ── Terraform Version Lock ─────────────────────
# "Minimum ye version chahiye Terraform ka"
terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"    # AWS ka official provider
      version = "~> 5.0"           # Version 5.x use karo
    }
  }
}


# ── AWS Provider Setup ─────────────────────────
# "AWS se baat karo, Mumbai region mein"
provider "aws" {
  region = var.aws_region           # variables.tf se aayega (default: ap-south-1)

  # Tags jo HAR resource pe lagenge automatically
  default_tags {
    tags = {
      Project     = "EmergencyQ"
      ManagedBy   = "Terraform"
      Environment = var.environment  # dev / staging / prod
    }
  }
}
