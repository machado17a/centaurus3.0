import os
# Este script revela o caminho da pasta de modelos do insightface
caminho_modelos = os.path.join(os.path.expanduser('~'), '.insightface', 'models')
print(f"Copie este caminho: {caminho_modelos}")