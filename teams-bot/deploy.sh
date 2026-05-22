#!/bin/bash

# Configuration
VPS_IP="217.216.108.16"
VPS_PORT="8822"
VPS_USER="root"
REMOTE_DIR="/root/room_booking_nlp"

echo "🚀 Deploying to VPS: $VPS_IP:$VPS_PORT..."

# Go to script directory
cd "$(dirname "$0")"

# Sync teams-bot folder to VPS
rsync -avz -e "ssh -p $VPS_PORT" \
    --exclude 'venv' \
    --exclude '__pycache__' \
    --exclude 'db.sqlite3' \
    --exclude '.git' \
    --exclude '.env' \
    ./ "$VPS_USER@$VPS_IP:$REMOTE_DIR"

# Run docker-compose on VPS
ssh -p $VPS_PORT "$VPS_USER@$VPS_IP" << EOF
    cd $REMOTE_DIR
    # Make sure .env exists, or create from .env.example if it doesn't
    if [ ! -f .env ]; then
        if [ -f .env.example ]; then
            cp .env.example .env
        else
            touch .env
        fi
    fi

    # Merge DB credentials from the main project's .env if it exists
    if [ -f ../ECE-BookingSystem/.env ]; then
        echo "🔑 Found ECE-BookingSystem/.env, merging database configurations..."
        grep -E '^(POSTGRES_|SQL_)' ../ECE-BookingSystem/.env | while read -r line; do
            var_name=\$(echo "\$line" | cut -d'=' -f1)
            # Remove existing variable from .env
            sed -i "/^\$var_name=/d" .env 2>/dev/null || sed -i "" "/^\$var_name=/d" .env
            echo "\$line" >> .env
        done
    fi

    docker compose up -d --build
    # Run migrations
    docker compose exec -T web python manage.py migrate
    # Create default rooms if needed (optional but helpful)
    # docker compose exec -T web python manage.py shell -c "from bookings.models import Room; Room.objects.get_or_create(room_id='406-3', defaults={'name': 'ห้องประชุม 1', 'room_type': 'ห้องประชุม', 'capacity': 60})"
EOF

echo "✅ Deployment trigger sent."
