#!/bin/bash

echo "🧹 === NETTOYAGE DES FICHIERS TEMPORAIRES ==="
echo ""

# Liste des fichiers à supprimer
FILES_TO_DELETE=(
    "manage_working.py"
    "manage_with_logs.py" 
    "manage_logs_copy.log"
    "output.log"
    "check_logs_location.sh"
    "diagnostic_scheduler.sh"
    "restart_scheduler.sh"
    "test_logs.sh"
    "test_logs_complete.sh"
    "test_show_logs.sh"
    "test_sync.sh"
)

echo "📋 Fichiers à supprimer :"
for file in "${FILES_TO_DELETE[@]}"; do
    if [ -f "$file" ]; then
        echo "   ✅ $file (existe)"
    else
        echo "   ❌ $file (n'existe pas)"
    fi
done

echo ""
read -p "🤔 Voulez-vous supprimer ces fichiers ? (y/N): " confirm

if [[ $confirm == [yY] || $confirm == [yY][eE][sS] ]]; then
    echo ""
    echo "🗑️ Suppression en cours..."
    
    for file in "${FILES_TO_DELETE[@]}"; do
        if [ -f "$file" ]; then
            rm "$file"
            echo "   ✅ Supprimé: $file"
        fi
    done
    
    echo ""
    echo "✨ Nettoyage terminé !"
    echo ""
    echo "📁 Fichiers conservés importants :"
    echo "   ✅ manage.py (version finale avec logging)"
    echo "   ✅ logs_local/ (dossier des logs synchronisés)"
    echo "   ✅ docker-compose.yml (avec volume logs configuré)"
    
else
    echo ""
    echo "❌ Nettoyage annulé."
fi

echo ""
echo "🎯 Résumé final :"
echo "   - Le logging fonctionne dans manage.py"
echo "   - Les logs sont synchronisés dans logs_local/"
echo "   - Le scheduler nécessite une réactivation manuelle"
