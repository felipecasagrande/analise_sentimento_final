# -*- coding: utf-8 -*-
"""
Coleta automatizada de tweets sobre 'tarifaço' com Nitter (20 instâncias + proxy rotativo)
Executa automaticamente às 6h da manhã todos os dias.
Autor: Mickaio Gabriel
"""

import time, random, urllib.parse, datetime, threading
import requests
from requests.adapters import HTTPAdapter, Retry
from bs4 import BeautifulSoup
import pandas as pd
from pathlib import Path
import schedule

# ==========================
# ⚙️ CONFIGURAÇÕES
# ==========================
CONSULTA = "tarifaço lang:pt -is:retweet"
LIMITE = 1000
CSV_SAIDA = Path("tweets_tarifaco_auto.csv")
LOG_SAIDA = Path("coletas_diarias.csv")

# 20 instâncias Nitter (rotativas)
NITTERS = [
    "https://nitter.net",
    "https://nitter.poast.org",
    "https://nitter.it",
    "https://nitter.hu",
    "https://nitter.spaceint.fr",
    "https://nitter.woodland.cafe",
    "https://nitter.plus.st",
    "https://nitter.lucabased.xyz",
    "https://nitter.salastil.com",
    "https://nitter.bus-hit.me",
    "https://nitter.sneed.network",
    "https://nitter.foss.wtf",
    "https://nitter.freedit.eu",
    "https://nitter.kavin.rocks",
    "https://nitter.uni-sonia.com",
    "https://nitter.pw",
    "https://nitter.projectsegfau.lt",
    "https://nitter.catsarch.com",
    "https://nitter.mint.lgbt",
    "https://nitter.weiler.rocks"
]

# Proxies
PROXIES = [
    None,
    {"http": "http://103.83.232.122:80", "https": "http://103.83.232.122:80"},
    {"http": "http://103.180.122.52:80", "https": "http://103.180.122.52:80"},
    {"http": "http://103.152.112.120:80", "https": "http://103.152.112.120:80"},
    {"http": "http://190.61.84.166:9812", "https": "http://190.61.84.166:9812"},
    {"http": "http://103.79.96.169:4153", "https": "http://103.79.96.169:4153"},
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.6",
    "Connection": "close",
}

# ==========================
# HTTP
# ==========================
def make_session():
    s = requests.Session()
    retries = Retry(total=2, connect=2, read=2, backoff_factor=0.7)
    adapter = HTTPAdapter(max_retries=retries, pool_connections=20, pool_maxsize=20)
    s.mount("http://", adapter)
    s.mount("https://", adapter)
    s.headers.update(HEADERS)
    return s


def fetch_page(session, base, query, cursor=None, proxies=None, timeout=15):
    url = f"{base}/search?f=tweets&q={urllib.parse.quote(query)}"
    if cursor:
        url += f"&cursor={urllib.parse.quote(cursor)}"

    r = session.get(url, timeout=timeout, proxies=proxies)
    if r.status_code != 200 or not r.text:
        raise RuntimeError(f"HTTP {r.status_code} em {base}")

    soup = BeautifulSoup(r.text, "html.parser")
    items = []
    for card in soup.select("div.timeline-item"):
        content = card.select_one(".tweet-content")
        texto = " ".join(content.stripped_strings) if content else ""
        user_a = card.select_one("a.username")
        usuario = user_a.get_text(strip=True).lstrip("@") if user_a else ""
        date_a = card.select_one("a.tweet-date")
        data = date_a.get("title") if date_a and date_a.has_attr("title") else ""
        link = base + date_a.get("href") if date_a and date_a.has_attr("href") else ""
        if texto:
            items.append({"data": data, "usuario": usuario, "texto": texto, "link": link})

    next_a = soup.select_one("div.show-more a")
    next_cursor = None
    if next_a and next_a.has_attr("href") and "cursor=" in next_a["href"]:
        next_cursor = next_a["href"].split("cursor=", 1)[-1]
    return items, next_cursor


# ==========================
# Coleta com rotação automática de proxy
# ==========================
def coletar():
    coletados = []
    random.shuffle(NITTERS)
    proxy_index = 0

    for base in NITTERS:
        print(f"🔎 Buscando em: {base}")
        session = make_session()
        cursor = None

        while len(coletados) < LIMITE:
            try:
                proxy = PROXIES[proxy_index % len(PROXIES)]
                dados, cursor = fetch_page(session, base, CONSULTA, cursor, proxies=proxy)
                if not dados:
                    print("⚠️ Nenhum resultado, trocando instância…")
                    break
                coletados.extend(dados)
                print(f"📥 Coletados: {len(coletados)}")
                if not cursor:
                    break
                time.sleep(random.uniform(1.2, 2.5))
            except Exception as e:
                print(f"❌ Erro com proxy {proxy_index}: {e}")
                proxy_index = (proxy_index + 1) % len(PROXIES)
                print("🔄 Trocando proxy automaticamente…")
                break

        if len(coletados) >= LIMITE:
            break
    return coletados[:LIMITE]


# ==========================
# Exportação + Log diário
# ==========================
def salvar_csv(dados):
    df = pd.DataFrame(dados, columns=["data", "usuario", "texto", "link"])
    df.to_csv(CSV_SAIDA, index=False, encoding="utf-8-sig", sep=";")

    hoje = datetime.date.today().strftime("%Y-%m-%d")
    qtd = len(df)
    if LOG_SAIDA.exists():
        log = pd.read_csv(LOG_SAIDA)
    else:
        log = pd.DataFrame(columns=["data", "coletas"])
    if hoje in log["data"].values:
        log.loc[log["data"] == hoje, "coletas"] += qtd
    else:
        log = pd.concat([log, pd.DataFrame([[hoje, qtd]], columns=["data", "coletas"])])
    log.to_csv(LOG_SAIDA, index=False, encoding="utf-8-sig")

    print(f"\n✅ {qtd} tweets salvos em '{CSV_SAIDA}'")
    return qtd


# ==========================
# Agendador diário
# ==========================
def tarefa_diaria():
    print("🕕 Coleta automática iniciada às 06h…")
    dados = coletar()
    salvar_csv(dados)
    print("✅ Coleta do dia finalizada!")


def iniciar_agendamento():
    schedule.every().day.at("06:00").do(tarefa_diaria)

    print("⏱️ Aguardando horário de execução (06:00 AM)...")
    while True:
        schedule.run_pending()
        time.sleep(60)


if __name__ == "__main__":
    thread = threading.Thread(target=iniciar_agendamento)
    thread.start()
