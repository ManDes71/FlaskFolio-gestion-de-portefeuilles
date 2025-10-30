#!/bin/bash
echo "🧹 Nettoyage du conteneur Docker..."

# Supprimer les fichiers temporaires du conteneur
rm -f /app/test_logs.sh
rm -f /app/check_logs_location.sh
rm -f /app/diagnostic_scheduler.sh
rm -f /app/restart_scheduler.sh
rm -f /app/test_sync.sh
rm -f /app/manage_with_logs.py

echo "✅ Nettoyage du conteneur terminé"
ls -la /app/ | grep -E "(\.sh|test_)" || echo "🎯 Aucun fichier temporaire restant"
