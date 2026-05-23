# ══════════════════════════════════════════════
#  main.tf — EmergencyQ
#
#  YE FILE SABSE IMPORTANT HAI TERRAFORM MEIN.
#
#  Ye file kya karti hai?
#  AWS pe ACTUAL resources banati hai:
#    → VPC (Virtual Private Cloud) = tera private network
#    → Subnet = network ke andar chhote sections
#    → Security Group = firewall (kaun aa sakta hai, kaun nahi)
#    → EC2 Instance = server machine (Docker chalegi isme)
#    → RDS PostgreSQL = managed database
#    → S3 Bucket = ML model files store karne ke liye
#
#  IMPORTANT: Ye file kuch nahi banayegi jab tak
#  tu `terraform apply` nahi chalata.
#  Ye sirf "blueprint" hai — jaise ghar ka naksha.
# ══════════════════════════════════════════════


# ──────────────────────────────────────────────
#  DATA SOURCE: Latest Ubuntu AMI
# ──────────────────────────────────────────────
# AMI = Amazon Machine Image = OS ka template
# Ye automatically latest Ubuntu 22.04 dhundh leta hai
# Tujhe manually AMI ID yaad nahi rakhni padti

data "aws_ami" "ubuntu" {
  most_recent = true
  owners      = ["099720109477"]     # Canonical (Ubuntu ke makers)

  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}


# ──────────────────────────────────────────────
#  VPC — Virtual Private Cloud
# ──────────────────────────────────────────────
# VPC = Tera private network AWS mein
# Jaise tera ghar ka WiFi network hota hai —
# bahar wale directly access nahi kar sakte
# jab tak tu allow na kare.

resource "aws_vpc" "main" {
  cidr_block           = "10.0.0.0/16"       # IP range: 10.0.0.0 - 10.0.255.255 (65K IPs)
  enable_dns_support   = true                  # DNS kaam kare VPC ke andar
  enable_dns_hostnames = true                  # Servers ko DNS names milein

  tags = {
    Name = "${var.project_name}-vpc"
  }
}


# ──────────────────────────────────────────────
#  SUBNETS — Network ke Sections
# ──────────────────────────────────────────────
# Subnet = VPC ke andar chhote sections
# Kyun? Alag-alag resources ko alag sections mein rakhna
# (jaise ghar mein rooms hote hain — kitchen, bedroom, bathroom)

# Public Subnet 1 — Ye internet se accessible hai
resource "aws_subnet" "public_1" {
  vpc_id                  = aws_vpc.main.id
  cidr_block              = "10.0.1.0/24"       # 256 IPs
  availability_zone       = "${var.aws_region}a"  # Mumbai zone A
  map_public_ip_on_launch = true                  # EC2 ko automatic public IP mile

  tags = {
    Name = "${var.project_name}-public-1"
  }
}

# Public Subnet 2 — RDS ke liye 2 zones chahiye (AWS requirement)
resource "aws_subnet" "public_2" {
  vpc_id                  = aws_vpc.main.id
  cidr_block              = "10.0.2.0/24"
  availability_zone       = "${var.aws_region}b"  # Mumbai zone B
  map_public_ip_on_launch = true

  tags = {
    Name = "${var.project_name}-public-2"
  }
}


# ──────────────────────────────────────────────
#  INTERNET GATEWAY — Bahar se access
# ──────────────────────────────────────────────
# Internet Gateway = Tera VPC ka main gate
# Bina iske koi bhi server internet se baat nahi kar sakta

resource "aws_internet_gateway" "igw" {
  vpc_id = aws_vpc.main.id

  tags = {
    Name = "${var.project_name}-igw"
  }
}


# ──────────────────────────────────────────────
#  ROUTE TABLE — Traffic kahan jaaye
# ──────────────────────────────────────────────
# Route Table = Traffic directions
# "Internet ki taraf jaana hai? Internet Gateway se jao"

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block = "0.0.0.0/0"                    # Koi bhi destination
    gateway_id = aws_internet_gateway.igw.id     # Internet Gateway se jao
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


# ──────────────────────────────────────────────
#  SECURITY GROUP — Firewall Rules
# ──────────────────────────────────────────────
# Security Group = Darwaze pe guard
# "Kaun andar aa sakta hai, kaunse port pe"

resource "aws_security_group" "app_sg" {
  name_prefix = "${var.project_name}-app-"
  vpc_id      = aws_vpc.main.id
  description = "EmergencyQ app server security group"

  # ── INBOUND RULES (kaun aa sakta hai) ────────

  # SSH access (port 22) — tere laptop se server pe jaane ke liye
  ingress {
    description = "SSH"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]     # TODO: Production mein apna IP daalo
  }

  # HTTP (port 80) — Frontend access
  ingress {
    description = "HTTP"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]     # Sabko allow (public website)
  }

  # HTTPS (port 443) — Secure access
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



  # ── OUTBOUND RULES (bahar kahan ja sakta hai) ──
  # Sab jagah ja sakta hai (updates download, Docker Hub, etc.)
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

# ──────────────────────────────────────────────
# ❌ RDS SECURITY GROUP — SKIP (RDS already bana hua hai AWS pe)
# Tera existing RDS: 
# Dobara banane ki zaroorat nahi — extra cost aur conflict hoga
# ──────────────────────────────────────────────
# resource "aws_security_group" "db_sg" {
#   name_prefix = "${var.project_name}-db-"
#   vpc_id      = aws_vpc.main.id
#   description = "EmergencyQ database security group"
#
#   ingress {
#     description     = "PostgreSQL from app server"
#     from_port       = 5432
#     to_port         = 5432
#     protocol        = "tcp"
#     security_groups = [aws_security_group.app_sg.id]
#   }
#
#   egress {
#     from_port   = 0
#     to_port     = 0
#     protocol    = "-1"
#     cidr_blocks = ["0.0.0.0/0"]
#   }
#
#   tags = {
#     Name = "${var.project_name}-db-sg"
#   }
# }


# ──────────────────────────────────────────────
#  EC2 INSTANCE — App Server
# ──────────────────────────────────────────────
# EC2 = Elastic Compute Cloud = Virtual server
# Ye tera main server hai jahan Docker containers chalenge

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

  # Server start hote hi ye commands automatically chalenge
  # Docker install + project clone + docker-compose up
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

    # ubuntu user ko docker group mein daalo (sudo na lagana pade)
    usermod -aG docker ubuntu

    echo "✅ Server ready! Docker installed."
    echo "Next: git clone your repo and run docker-compose up"
  EOF

  tags = {
    Name = "${var.project_name}-app-server"
  }
}





# ──────────────────────────────────────────────
#  S3 BUCKET — ML Model Storage
# ──────────────────────────────────────────────
# S3 = Simple Storage Service = Cloud mein file storage
# Trained DistilBERT model, label_encoder.pkl,
# icp_model.pkl — sab yahan rakh do.
# Server pe directly rakhne se agar server mita to model bhi gaya.

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
