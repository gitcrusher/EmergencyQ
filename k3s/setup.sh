#!/bin/bash
# ══════════════════════════════════════════════
#  k3s Setup & Deployment Script — EmergencyQ
#  Run this once on the EC2 server to:
#    1. Install k3s (lightweight Kubernetes)
#    2. Create secrets from the local .env file
#    3. Deploy all services to the cluster
# ══════════════════════════════════════════════
set -e

GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[1;34m'
NC='\033[0m'

echo -e "${BLUE}🚀 Step 1: Installing k3s...${NC}"
curl -sfL https://get.k3s.io | sh -

echo -e "${BLUE}⏳ Waiting for k3s node to be ready...${NC}"
sleep 15

echo -e "${BLUE}🔑 Setting up kubeconfig for ubuntu user...${NC}"
mkdir -p /home/ubuntu/.kube
sudo cp /etc/rancher/k3s/k3s.yaml /home/ubuntu/.kube/config
sudo chown -R ubuntu:ubuntu /home/ubuntu/.kube
export KUBECONFIG=/home/ubuntu/.kube/config

# Persist KUBECONFIG in shell profile
if ! grep -q "KUBECONFIG" /home/ubuntu/.bashrc; then
    echo "export KUBECONFIG=/home/ubuntu/.kube/config" >> /home/ubuntu/.bashrc
fi

echo -e "${GREEN}✅ Node is ready:${NC}"
kubectl get nodes

echo -e "${BLUE}📦 Step 2: Creating namespace and secrets...${NC}"
kubectl apply -f k3s/namespace.yaml

# Generate secrets dynamically from the local .env file — no secrets in Git
if [ -f .env ]; then
    echo -e "${GREEN}🔑 Found .env — creating Kubernetes secret...${NC}"
    kubectl create secret generic emergencyq-secrets \
      --from-env-file=.env \
      -n emergencyq \
      --dry-run=client -o yaml | kubectl apply -f -
else
    echo -e "${RED}❌ .env file not found. Create one on the server before running this script.${NC}"
    exit 1
fi

echo -e "${BLUE}⚙️  Applying ConfigMap...${NC}"
kubectl apply -f k3s/configmap.yaml -n emergencyq

echo -e "${BLUE}⚙️  Applying Monitoring ConfigMaps...${NC}"
kubectl apply -f k3s/prometheus-configmap.yaml -n emergencyq
kubectl apply -f k3s/grafana-datasources-configmap.yaml -n emergencyq
kubectl apply -f k3s/grafana-providers-configmap.yaml -n emergencyq
kubectl apply -f k3s/grafana-dashboards-configmap.yaml -n emergencyq

echo -e "${BLUE}🚀 Step 3: Deploying App and Monitoring...${NC}"
kubectl apply -f k3s/backend-deployment.yaml -n emergencyq
kubectl apply -f k3s/backend-service.yaml -n emergencyq
kubectl apply -f k3s/frontend-deployment.yaml -n emergencyq
kubectl apply -f k3s/frontend-service.yaml -n emergencyq
kubectl apply -f k3s/prometheus-deployment.yaml -n emergencyq
kubectl apply -f k3s/grafana-deployment.yaml -n emergencyq

echo -e "${BLUE}🌐 Applying Ingress routing rules...${NC}"
kubectl apply -f k3s/ingress.yaml -n emergencyq

echo -e "${GREEN}🎉 Done! Deployment status:${NC}"
kubectl get deployments -n emergencyq
kubectl get pods -n emergencyq
