"""Leitura de atas fictícias em uma pasta única de um repositório público GitHub."""
import re
import unicodedata
import requests

REPO = "karolcastro/Reprograma_IA_Agente_de_Projetos"
PASTA = "dados_exemplo/atas"
BASE = f"https://api.github.com/repos/{REPO}/contents/{PASTA}"

def normalizar(texto):
    texto = unicodedata.normalize("NFKD", texto.lower())
    return "".join(c for c in texto if not unicodedata.combining(c))

def listar_atas():
    resposta = requests.get(BASE, params={"ref": "main"}, timeout=15,
                            headers={"Accept": "application/vnd.github+json"})
    resposta.raise_for_status()
    return [item for item in resposta.json()
            if item.get("type") == "file" and item["name"].lower().endswith(".txt")]

def atas_do_projeto(nome_projeto):
    """Confere o cabeçalho Projeto: em cada ata, sem confiar só no nome do arquivo."""
    arquivos = listar_atas()
    encontrados = []
    for arquivo in arquivos:
        url = arquivo.get("download_url")
        if not url:
            continue
        resposta = requests.get(url, timeout=15)
        resposta.raise_for_status()
        conteudo = resposta.content.decode("utf-8-sig")
        match = re.search(r"^Projeto:\s*(.+)$", conteudo, re.MULTILINE | re.IGNORECASE)
        if match and normalizar(match.group(1).strip()) == normalizar(nome_projeto.strip()):
            data = re.search(r"^Data:\s*(\d{2}/\d{2}/\d{4})", conteudo, re.MULTILINE)
            encontrados.append({
                "arquivo": arquivo["name"],
                "data": data.group(1) if data else "Não informada",
                "texto": conteudo,
            })
    encontrados.sort(key=lambda a: a["arquivo"])
    return encontrados

def extrair_trechos(texto):
    categorias = {
        "Pendências": ("pendência:", "pendente:", "ação:"),
        "Decisões": ("decisão:",),
        "Riscos e gargalos": ("risco:", "gargalo:"),
        "Prazos": ("prazo:", "prazo da entrega:", "próxima reunião:"),
        "Atualizações": ("atualização:", "situação:"),
    }
    linhas = [linha.strip() for linha in texto.splitlines() if linha.strip()]
    return {
        categoria: [linha for linha in linhas if any(
            normalizar(linha).startswith(normalizar(p)) for p in prefixos
        )]
        for categoria, prefixos in categorias.items()
    }
