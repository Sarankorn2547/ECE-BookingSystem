#!/bin/bash

# Configuration
VPS_IP="217.216.108.16"
VPS_PORT="8822"
VPS_USER="root"
REMOTE_DIR="/root/room_booking_nlp"

echo "🚀 Deploying to VPS: $VPS_IP:$VPS_PORT..."

# Sync ONLY Backend folder to VPS
rsync -avz -e "ssh -p $VPS_PORT" \
    --exclude 'venv' \
    --exclude '__pycache__' \
    --exclude 'db.sqlite3' \
    --exclude '.git' \
    ./Backend/ "$VPS_USER@$VPS_IP:$REMOTE_DIR"

# Run docker-compose on VPS
ssh -p $VPS_PORT "$VPS_USER@$VPS_IP" << EOF
    cd $REMOTE_DIR
    # Make sure .env exists, or create from .env.example if it doesn't (manual step usually better)
    if [ ! -f .env ]; then
        echo "⚠️ .env file missing on VPS. Please create it at $REMOTE_DIR/.env"
        # cp .env.example .env # Optional: auto-copy but user needs to edit it
    fi
    docker compose up -d --build
    # Run migrations
    docker compose exec -T web python manage.py migrate
    # Create default rooms if needed (optional but helpful)
    # docker compose exec -T web python manage.py shell -c "from bookings.models import Room; Room.objects.get_or_create(room_id='406-3', defaults={'name': 'ห้องประชุม 1', 'room_type': 'ห้องประชุม', 'capacity': 60})"
EOF

echo "✅ Deployment trigger sent."
