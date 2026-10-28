#!/bin/bash
# Demo en vivo: corre el agente real sobre los 3 rubros (gasta API, ~3-5 min).
# Uso: bash demo_vivo.sh [videos/prueba.mp4]
set -e
VIDEO="${1:-videos/prueba.mp4}"
for NEG in jugueria ropa belleza; do
  echo "================================================================"
  echo ">>> Rubro: $NEG"
  echo "================================================================"
  python main.py "$VIDEO" --negocio "negocios/$NEG.txt" --no-interactivo
done
echo ""
echo "Comparación multi-rubro lista. Archivos:"
ls -la videos/*_guiones_verificados_*.txt
