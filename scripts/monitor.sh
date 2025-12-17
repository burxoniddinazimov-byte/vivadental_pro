#!/bin/bash

set -e

echo "📊 VivaDental Monitoring Dashboard"

# System metrics
echo "=== SYSTEM METRICS ==="
echo "CPU Usage: $(top -bn1 | grep "Cpu(s)" | awk '{print $2}')%"
echo "Memory Usage: $(free -m | awk 'NR==2{printf "%.2f%%", $3*100/$2}')"
echo "Disk Usage: $(df -h / | awk 'NR==2{print $5}')"

# Docker containers
echo -e "\n=== DOCKER CONTAINERS ==="
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# Service health checks
echo -e "\n=== SERVICE HEALTH ==="

check_service() {
    SERVICE=$1
    URL=$2
    if curl -f -s $URL > /dev/null; then
        echo "✅ $SERVICE: Healthy"
    else
        echo "❌ $SERVICE: Unhealthy"
    fi
}

check_service "Backend API" "http://localhost:8000/api/health"
check_service "Frontend" "http://localhost"
check_service "PostgreSQL" "-"
check_service "Redis" "-"

# Database metrics
echo -e "\n=== DATABASE METRICS ==="
docker-compose exec postgres psql -U $POSTGRES_USER $POSTGRES_DB -c "
SELECT 
    schemaname,
    relname,
    n_live_tup as live_rows,
    n_dead_tup as dead_rows,
    pg_size_pretty(pg_total_relation_size(relid)) as total_size
FROM pg_stat_user_tables 
ORDER BY n_live_tup DESC 
LIMIT 10;
"

# Application metrics
echo -e "\n=== APPLICATION METRICS ==="
echo "Total Patients: $(curl -s http://localhost:8000/api/patients/count)"
echo "Today's Appointments: $(curl -s http://localhost:8000/api/appointments/today/count)"
echo "Pending Invoices: $(curl -s http://localhost:8000/api/finance/invoices/pending/count)"

# Prometheus metrics
echo -e "\n=== PROMETHEUS METRICS ==="
curl -s http://localhost:9090/api/v1/query?query=up | jq -r '.data.result[] | "\(.metric.job): \(.value[1])"'

echo -e "\n🎯 Monitoring completed at $(date)"