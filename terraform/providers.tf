
#  Terraform tells : "we have to use  AWS"
#
#  Provider = cloud company


#  This file only setup connection 
#  Actual resources (servers, DB) main.tf mein hain.

# Minimum version of terraform should be 1.5.0
terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"   
      version = "~> 5.0"           
    }
  }
}


#  AWS Provider Setup 
# "itneract with aws of mumbai Region"
provider "aws" {
  region = var.aws_region          
  # tags will be applied to all resources
  default_tags {
    tags = {
      Project     = "EmergencyQ"
      ManagedBy   = "Terraform"
      Environment = var.environment  # dev / staging / prod
    }
  }
}
