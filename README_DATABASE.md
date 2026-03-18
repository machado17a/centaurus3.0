# Sistema de Banco de Dados Criptografado - Centaurus

## 📋 Visão Geral

O sistema agora utiliza um **banco de dados SQLite criptografado** (SQLCipher) para armazenar todas as verificações e imagens, substituindo o antigo sistema de pastas e arquivos CSV.

---

## 🔐 Segurança

- **Criptografia**: SQLCipher 4.x com AES-256
- **Senha**: Hardcoded nos arquivos (não altere!)
- **Arquivo**: `C:\ProgramData\Centaurus\verificacoes\verificacoes.db`

---

## 📊 Estrutura do Banco de Dados

### Tabelas Principais:

1. **maquinas** - Informações das máquinas que executam o sistema
2. **verificacoes** - Registro de todas as verificações realizadas
3. **imagens** - Imagens das faces (documento e webcam) como BLOBs
4. **casos_positivos** - Verificações com similaridade > 70%
5. **casos_suspeitos** - Verificações < 70% + screenshot da tela resultado
6. **auditoria_documentos** - Verificações do modo "documento"

---

## 🔧 Instalação

### 1. Instalar dependência adicional:

```bash
pip install sqlcipher3-binary
```

Ou usando o arquivo de requirements atualizado:

```bash
pip install -r requiriments_updated.txt
```

---

## 💻 Uso Normal

O sistema funciona **exatamente como antes**, mas agora salva tudo no banco de dados criptografado ao invés de criar pastas e arquivos.

### O que mudou (internamente):

❌ **Antes** (arquivos):
```
verificacoes/
├── log_verificacoes_2025-11-10.csv
├── captura_de_documentos/
│   ├── documento_20251110_143022.png
│   └── webcam_20251110_143022.png
├── casos_positivos/
│   ├── positivo_doc_20251110_143155.png
│   └── positivo_webcam_20251110_143155.png
└── resultados_suspeitos/
    └── resultado_20251110_143300.png
```

✅ **Agora** (banco de dados):
```
verificacoes/
└── verificacoes.db  (arquivo único criptografado)
```

---

## 🔓 Como Descriptografar o Banco de Dados

### Quando usar:
- Você precisa **analisar os dados** em ferramentas como DBeaver, DB Browser, etc.
- Você quer **fazer backup** para análise externa
- Você precisa **exportar relatórios** personalizados

### Passo a Passo:

1. **Copie o arquivo criptografado** do PC de produção:
   ```
   C:\ProgramData\Centaurus\verificacoes\verificacoes.db
   ```

2. **Execute o utilitário de descriptografia**:

   **Modo Interativo:**
   ```bash
   python descriptografar_db.py
   ```
   - Siga as instruções na tela
   - Digite o caminho do arquivo `.db` criptografado
   - O arquivo descriptografado será gerado automaticamente

   **Modo Linha de Comando:**
   ```bash
   python descriptografar_db.py "caminho/para/verificacoes.db" "saida_descriptografada.db"
   ```

3. **Abra no DBeaver/DB Browser**:
   - Agora você pode abrir o arquivo `*_descriptografado_*.db` normalmente
   - Todas as tabelas e imagens estarão acessíveis

---

## 📈 Consultando os Dados

### Exemplos de Consultas SQL (após descriptografar):

```sql
-- Total de verificações por status
SELECT status, COUNT(*) as total
FROM verificacoes
GROUP BY status;

-- Verificações de hoje
SELECT * FROM verificacoes
WHERE DATE(timestamp) = DATE('now')
ORDER BY timestamp DESC;

-- Casos suspeitos com informações da máquina
SELECT 
    v.id,
    v.timestamp,
    v.similaridade,
    v.status,
    m.hostname,
    m.username
FROM verificacoes v
INNER JOIN casos_suspeitos cs ON v.id = cs.verificacao_id
INNER JOIN maquinas m ON v.maquina_id = m.id
ORDER BY v.timestamp DESC;

-- Verificações por máquina
SELECT 
    m.hostname,
    COUNT(v.id) as total_verificacoes,
    AVG(v.similaridade) as media_similaridade
FROM maquinas m
LEFT JOIN verificacoes v ON m.id = v.maquina_id
GROUP BY m.hostname;
```

### Exportar Imagens:

As imagens estão armazenadas como BLOBs na tabela `imagens`. Para extraí-las, você precisará de um script Python ou ferramenta específica.

---

## ⚠️ Avisos Importantes

### ❗ Senha Hardcoded

A senha está **hardcoded** nos arquivos:
- `database_manager.py` (linha 8)
- `descriptografar_db.py` (linha 6)

**NUNCA ALTERE A SENHA** depois de começar a usar o sistema, ou você perderá acesso aos dados antigos!

### ❗ Backup

O arquivo `.db` é **único e crítico**. Faça backups regulares:

```bash
# Exemplo de backup simples
copy "C:\ProgramData\Centaurus\verificacoes\verificacoes.db" "D:\Backups\centaurus_backup_%date%.db"
```

### ❗ Compatibilidade

- O arquivo criptografado **NÃO pode ser aberto** diretamente no DBeaver/DB Browser
- Você **DEVE descriptografar** primeiro usando o utilitário fornecido
- O arquivo descriptografado **NÃO está protegido** - delete após análise

---

## 🛠️ Troubleshooting

### Erro: "sqlcipher3 não encontrado"

```bash
pip install sqlcipher3-binary
```

### Erro: "Senha incorreta"

- Verifique se você está usando o arquivo `.db` correto
- Confirme que a senha no `descriptografar_db.py` é a mesma do `database_manager.py`
- O arquivo pode estar corrompido - restaure do backup

### Erro ao compilar com PyInstaller

Se houver problemas ao gerar o `.exe`, adicione ao arquivo `.spec`:

```python
hiddenimports=['sqlcipher3', '_sqlcipher3'],
```

---

## 📞 Suporte

Desenvolvido por: **RFH/DCRIM/INI/DPA/PF**

Para questões técnicas, consulte a documentação interna ou contate o desenvolvedor.

---

## 📝 Changelog

### Versão 1.6
- ✅ Implementado banco de dados criptografado (SQLCipher)
- ✅ Criado utilitário de descriptografia
- ✅ Tabela de informações de máquinas
- ✅ Armazenamento de imagens como BLOBs
- ✅ Eliminadas pastas de arquivos
- ✅ Eliminados arquivos CSV
