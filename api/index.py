import sys
import os

# Adiciona a raiz do projeto ao path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app

# Exporta a aplicação Flask para a Vercel
app = app
