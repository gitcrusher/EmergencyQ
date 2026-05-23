
#  define  Variables like function's and its parameters



#  AWS Region 
variable "aws_region" {
  description = "in which region aws resources are created"
  type        = string
  default     = "ap-south-1"     
}


#  Environment 
variable "environment" {
  description = "dev, staging, ya prod tells what sthe environment"
  type        = string
  default     = "dev"
}


#  Project Name 
variable "project_name" {
  description = "project's name - used for resource naming"
  type        = string
  default     = "emergencyq"
}


#  EC2 Instance Type 
variable "instance_type" {
  description = "EC2 server size (CPU + RAM)"
  type        = string
  default     = "t3.medium"     
}


#  SSH Key 
variable "key_pair_name" {
  description = "SSH access key pair name"
  type        = string
  default     = "emergencyq-key"   #  your key pair name
}
