#!/bin/bash
# ══════════════════════════════════════════════════════════════════
#  k3s Setup & Deployment Automation Script — EmergencyQ
# ══════════════════════════════════════════════════════════════════
set -e

# Pretty logging colors
GREEN='\033[0;32m'
BLUE='\033[1;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Step 1: Installing k3s (Lightweight Kubernetes)...${NC}"
# Install k3s securely
curl -sfL https://get.k3s.io | sh -

# Wait for node to become active
echo -e "${BLUE}⏳ Waiting for k3s node to boot up...${NC}"
sleep 15

echo -e "${BLUE}🔑 Configuring Kubeconfig permissions for 'ubuntu' user...${NC}"
# Set up kubeconfig so 'kubectl' can be run without using 'sudo'
mkdir -p /home/ubuntu/.kube
sudo cp /etc/rancher/k3s/k3s.yaml /home/ubuntu/.kube/config
sudo chown -R ubuntu:ubuntu /home/ubuntu/.kube
export KUBECONFIG=/home/ubuntu/.kube/config

# Add KUBECONFIG environment variable to shell profile permanently
if ! grep -q "KUBECONFIG" /home/ubuntu/.bashrc; then
    echo "export KUBECONFIG=/home/ubuntu/.kube/config" >> /home/ubuntu/.bashrc
fi

echo -e "${GREEN}✅ Kubernetes Node is ready! Node status:${NC}"
kubectl get nodes

echo -e "${BLUE}📦 Step 2: Setting up Namespace and Secrets...${NC}"
# Create the namespace
kubectl apply -f k8s/namespace.yaml

# Generate K8s secret dynamically from the server's local .env file
if [ -f .env ]; then
    echo -e "${GREEN}🔑 Successfully found .env file! Creating secrets dynamically...${NC}"
    kubectl create secret generic emergencyq-secrets \
      --from-env-file=.env \
      -n emergencyq \
      --dry-run=client -o yaml | kubectl apply -f -
else
    echo -e "${YELLOW}⚠️ .env file not found. Falling back to placeholder secret.yaml...${NC}"
    kubectl apply -f k8s/secret.yaml -n emergencyq
fi

# Apply ConfigMaps
echo -e "${BLUE}⚙️ Applying ConfigMaps...${NC}"
kubectl apply -f k8s/configmap.yaml -n emergencyq

# Deploy Services to Kubernetes
echo -e "${BLUE}🚀 Step 3: Deploying Services (Backend & Frontend) to Kubernetes...${NC}"
kubectl apply -f k8s/backend-deployment.yaml -n emergencyq
kubectl apply -f k8s/backend-service.yaml -n emergencyq
kubectl apply -f k8s/frontend-deployment.yaml -n emergencyq
kubectl apply -f k8s/frontend-service.yaml -n emergencyq

# Apply Ingress configuration for web routing
echo -e "${BLUE}🌐 Applying Ingress routing rules...${NC}"
kubectl apply -f k8s/ingress.yaml -n emergencyq

echo -e "${GREEN}🎉 Step 4: Kubernetes Setup & Deployment complete!${NC}"
echo -e "${GREEN}Active Deployments:${NC}"
kubectl get deployments -n emergencyq
echo -e "${GREEN}Running Pods:${NC}"
kubectl get pods -n emergencyq
