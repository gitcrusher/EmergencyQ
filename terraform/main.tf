
#  AWS creates resource :
#    → VPC (Virtual Private Cloud) = private network
#    → Subnet = inside network small sections
#    → Security Group = firewall
#    → EC2 Instance = server machine ( to run  Docker)
#    → RDS PostgreSQL = managed database
#    → S3 Bucket = to store ml model files.



#  DATA SOURCE: Latest Ubuntu AMI

# AMI = Amazon Machine Image = OS's template
# automatically finds latest Ubuntu 22.04 
# we dont have to manually remmeber the ami id 

data "aws_ami" "ubuntu" {
  most_recent = true
  owners      = ["099720109477"]     # Canonical (Ubuntu's makers)

  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}


#  VPC — Virtual Private Cloud

# VPC = private network
# no body could access the network without your permission

resource "aws_vpc" "main" {
  cidr_block           = "10.0.0.0/16"       # IP range: 10.0.0.0 - 10.0.255.255 (65K IPs)
  enable_dns_support   = true                  # DNS works inside VPC
  enable_dns_hostnames = true                  # Servers will get DNS names

  tags = {
    Name = "${var.project_name}-vpc"
  }
}



#  SUBNETS — Network's Sections

# Subnet = small section inside vpc

# Public Subnet 1 — accessible form internet
resource "aws_subnet" "public_1" {
  vpc_id                  = aws_vpc.main.id
  cidr_block              = "10.0.1.0/24"       # 256 IPs
  availability_zone       = "${var.aws_region}a"  # Mumbai zone A
  map_public_ip_on_launch = true                  # EC2 gets public ip automaticall
  
  tags = {
    Name = "${var.project_name}-public-1"
  }
}

# Public Subnet 2 — for RDS we need 2 zones according to AWS 
resource "aws_subnet" "public_2" {
  vpc_id                  = aws_vpc.main.id
  cidr_block              = "10.0.2.0/24"
  availability_zone       = "${var.aws_region}b"  # Mumbai zone B
  map_public_ip_on_launch = true

  tags = {
    Name = "${var.project_name}-public-2"
  }
}



#  INTERNET GATEWAY — access from out side

# Internet Gateway = main gate for vpc
# Without this , no server can communicate with the internet

resource "aws_internet_gateway" "igw" {
  vpc_id = aws_vpc.main.id

  tags = {
    Name = "${var.project_name}-igw"
  }
}



#  ROUTE TABLE — Traffic directions
#  if you wanna go towards internet go from the gateway created

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block = "0.0.0.0/0"                    # for any destination 
    gateway_id = aws_internet_gateway.igw.id     # internet gateway
  }

  tags = {
    Name = "${var.project_name}-public-rt"
  }
}

# Subnets ko route table se jodo
resource "aws_route_table_association" "public_1" {
  subnet_id      = aws_subnet.public_1.id
  route_table_id = aws_route_table.public.id
}

resource "aws_route_table_association" "public_2" {
  subnet_id      = aws_subnet.public_2.id
  route_table_id = aws_route_table.public.id
}


#  SECURITY GROUP — Firewall Rules

# Security Group = security protocol
# it tell who can come and also onto which port.

resource "aws_security_group" "app_sg" {
  name_prefix = "${var.project_name}-app-"
  vpc_id      = aws_vpc.main.id
  description = "EmergencyQ app server security group"

  #  INBOUND RULES 
  

  # SSH access (port 22) — 
  ingress {
    description = "SSH"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]     # TODO: in production add your ip 
  }

  # HTTP (port 80) — Frontend access
  ingress {
    description = "HTTP"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]     # allowed for all  (public website)
  }

  # HTTPS (port 443) — 
  ingress {
    description = "HTTPS"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # Backend API (port 8000)
  ingress {
    description = "FastAPI Backend"
    from_port   = 8000
    to_port     = 8000
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # Grafana Dashboard (port 3000) — disabled to save RAM on t3.small
  # Uncomment to re-enable Grafana
  # ingress {
  #   description = "Grafana"
  #   from_port   = 3000
  #   to_port     = 3000
  #   protocol    = "tcp"
  #   cidr_blocks = ["0.0.0.0/0"]
  # }

  # Prometheus UI (port 9090)
  ingress {
    description = "Prometheus"
    from_port   = 9090
    to_port     = 9090
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }



  # OUTBOUND RULES (bahar kahan ja sakta hai) 
  # all the time allowed
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"              # -1 = all protocols
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.project_name}-app-sg"
  }
}






#  EC2 INSTANCE — App Server

# EC2 = Elastic Compute Cloud = Virtual server

resource "aws_instance" "app_server" {
  ami                    = data.aws_ami.ubuntu.id         # Latest Ubuntu 22.04
  instance_type          = var.instance_type               # t3.medium (2 CPU, 4GB)
  key_name               = var.key_pair_name               # SSH key
  subnet_id              = aws_subnet.public_1.id
  vpc_security_group_ids = [aws_security_group.app_sg.id]

  # 30 GB storage (ML model + Docker images = space chahiye)
  root_block_device {
    volume_size = 30          # GB
    volume_type = "gp3"       # SSD (fast)
  }

  # Automatically installs Docker, clones the project repository, and starts the application using Docker Compose when the server boots.
  user_data = <<-EOF
    #!/bin/bash
    set -e

    # Create 4GB Swap Space (extremely important for free-tier 1GB RAM to run ML models without OOM)
    fallocate -l 4G /swapfile || dd if=/dev/zero of=/swapfile bs=1M count=4096
    chmod 600 /swapfile
    mkswap /swapfile
    swapon /swapfile
    echo '/swapfile none swap sw 0 0' >> /etc/fstab

    # System update
    apt-get update -y
    apt-get upgrade -y

    # Docker install
    apt-get install -y docker.io docker-compose-v2
    systemctl enable docker
    systemctl start docker

    # Add the ubuntu user to the Docker group to avoid using sudo with Docker commands.
    usermod -aG docker ubuntu

    echo "Server ready! Docker installed."
    echo "Next: git clone your repo and run docker-compose up"
  EOF

  tags = {
    Name = "${var.project_name}-app-server"
  }
}





#  S3 BUCKET — ML Model Storage

#S3 (Simple Storage Service) is cloud-based file storage used to securely store files such as trained DistilBERT models, `label_encoder.pkl`, and `icp_model.pkl`, ensuring they remain safe even if the server is deleted.

resource "aws_s3_bucket" "model_artifacts" {
  bucket = "${var.project_name}-models-${var.environment}"

  tags = {
    Name = "${var.project_name}-model-storage"
  }
}

# Versioning ON karo — galti se delete hua to recover ho sake
resource "aws_s3_bucket_versioning" "model_versioning" {
  bucket = aws_s3_bucket.model_artifacts.id

  versioning_configuration {
    status = "Enabled"
  }
}

# Public access BLOCK karo — models private rehne chahiye
resource "aws_s3_bucket_public_access_block" "model_block" {
  bucket = aws_s3_bucket.model_artifacts.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# ──────────────────────────────────────────────
#  ELASTIC IP — Static IP for Server
# ──────────────────────────────────────────────
# Elastic IP ensures that the public IP address remains constant
# even if the EC2 instance is stopped and started.
resource "aws_eip" "app_eip" {
  instance = aws_instance.app_server.id
  domain   = "vpc"

  tags = {
    Name = "${var.project_name}-app-eip"
  }
}
