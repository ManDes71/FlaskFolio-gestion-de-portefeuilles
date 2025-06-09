# pea_trading/services/live_scraper.py

import requests
from bs4 import BeautifulSoup
from datetime import datetime
import re
from pea_trading import db
from pea_trading.portfolios.stock import Stock
import json


def clean_price(text):
    match = re.search(r"(\d+[.,]?\d*)", text)
    if match:
        return float(match.group(1).replace(',', '.'))
    return None

def get_stock_info(stock_symbol):
    url = f"https://www.boursorama.com/cours/{stock_symbol}/"
    headers = {
        "User-Agent": "Mozilla/5.0"
    }
    
    response = requests.get(url, headers=headers)
    page_text = response.text

    # On cherche "fv_code_isin" et "fv_secteur_activite" dans le texte brut
    isin_match = re.search(r'"fv_code_isin":"(.*?)"', page_text)
    sector_match = re.search(r'"fv_secteur_activite":"(.*?)"', page_text)

    # Valeurs par défaut si on ne trouve rien
    isin_code = "ISIN non trouvé"
    code_yahoo = "Yahoo non trouvé"
    sector = "Secteur non trouvé"

    if isin_match:
        # Exemple: "FR001400J770_SRDAIR FRANCE"
        # On désérialise pour transformer les \uXXXX en caractères accentués
        full_isin = json.loads(f'"{isin_match.group(1)}"')  
        # Séparation en deux parties (ISIN et code Yahoo)
        parts = full_isin.split('_')
        isin_code = parts[0] if len(parts) > 0 else "ISIN non trouvé"
        code_yahoo = parts[1] if len(parts) > 1 else "Yahoo non trouvé"
    
    if sector_match:
        # Désérialise pour récupérer les accents
        sector = json.loads(f'"{sector_match.group(1)}"')

    return isin_code, code_yahoo, sector

def get_intraday_data(stock_symbol):
    url = f"https://www.boursorama.com/cours/{stock_symbol}/"
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        return {'ouverture': None, 'plus_haut': None, 'plus_bas': None, 'cloture': None}
    
    soup = BeautifulSoup(response.text, 'html.parser')

    data = {
        "ouverture": None,
        "plus_haut": None,
        "plus_bas": None,
        "cloture": None,
        "isin": None
    }

    try:
        for li in soup.select("ul.c-list--data li"):
            print("li : ",li)
            spans = li.find_all("span")
            print("spans : ",spans)
            if len(spans) >= 2:
                label = spans[0].text.strip().lower()
                print("label : ",label)
                value = clean_price(spans[1].text.strip())
                print("value : ",value)

                if "ouverture" in label:
                    data["ouverture"] = value
                elif "+ haut" in label:
                    data["plus_haut"] = value
                elif "+ bas" in label:
                    data["plus_bas"] = value
                elif "clôture" in label:
                    data["cloture"] = value

        # --- ISIN ---
        extra_info_div = soup.find("div", class_="c-faceplate__extra-info")
        if extra_info_div:
            dt_tags = extra_info_div.find_all("dt")
            dd_tags = extra_info_div.find_all("dd")
            for dt, dd in zip(dt_tags, dd_tags):
                if "ISIN" in dt.get_text(strip=True):
                    data["isin"] = dd.get_text(strip=True)
                    break

    except Exception as e:
        print(f"Erreur parsing intraday pour {stock_symbol} :", e)

    return data

def get_stock_prices(letter):
    """ Récupère la liste des actions éligibles PEA sur Boursorama
        en fonction de la première lettre, ainsi que leur prix
        et un code interne permettant de faire la requête. 
    """
    url = (
        "https://www.boursorama.com/bourse/actions/cotations/"
        f"?quotation_az_filter%5Bmarket%5D=1rPPX5"
        f"&quotation_az_filter%5Bletter%5D={letter}"
        f"&quotation_az_filter%5BpeaEligibility%5D=1"
    )
    headers = {"User-Agent": "Mozilla/5.0"}
    print(url)
    print("lettre ",letter)
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        print("Erreur lors de la récupération des données (boursorama - get_stock_prices)")
        return []
    
    soup = BeautifulSoup(response.text, "html.parser")
    main_content = soup.find("main", id="main-content")
    if main_content is None:
        print("❌ Élément #main-content introuvable.")
        return []
    table_container = main_content.find("div", class_="o-gutter u-hidden@sm-min")
    if table_container is None:
        print("❌ Élément .o-gutter.u-hidden@sm-min introuvable.")
        return []
    table = soup.select_one("table.c-table-top-flop")
    if table is None:
        print("❌ Tableau introuvable.")
        return []
    tbody = table.find("tbody", class_="c-table__body")
    if not tbody:
        print("❌ <tbody> du tableau non trouvé.")
        return []

    stock_data = []    
 
    for row in table.find_all("tr", class_="c-table__row"):
        data_json = row.get("data-ist-init")
        if not data_json:
            print("on continue")
            continue

        try:
            data = json.loads(data_json)
            #intraday = get_intraday_data(data.get("symbol"))
            #code_isin = intraday.get("isin")

            
            #name_tag = row.find("a")
            #name = name_tag.text.strip() if name_tag else "N/A"

            stock_data.append({
                #'isin': code_isin,
                'symbol': data.get("symbol"),
                'price': str(data.get("last")),
                'ouverture': str(data.get("previousClose", "")),
                'plus_haut': str(data.get("high", "")),
                'plus_bas': str(data.get("low", "")),
                'cloture': str(data.get("last", "")),
                'volume': str(data.get("totalVolume", "")),
            })    
            
        except Exception as e:
            print(f"⚠️ Erreur parsing ligne : {e}")

    #print(stock_data)

    
    return stock_data

