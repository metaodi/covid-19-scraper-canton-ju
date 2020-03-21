# -*- coding: utf-8 -*-

import requests
from bs4 import BeautifulSoup
import sqlite3
import re
import json
import dateparser
import traceback
import os

DATABASE_NAME = 'data.sqlite'
conn = sqlite3.connect(DATABASE_NAME)
c = conn.cursor()
c.execute(
    '''
    CREATE TABLE IF NOT EXISTS data (
        date text,
        time text,
        abbreviation_canton_and_fl text,
        ncumul_tested  integer,
        ncumul_conf integer,
        ncumul_hosp integer,
        ncumul_ICU integer,
        ncumul_vent integer,
        ncumul_released integer,
        ncumul_deceased integer,
        source text,
        UNIQUE(date, time, abbreviation_canton_and_fl)
    )
    '''
)
conn.commit()


def parse_page(soup, conn):
    data = {
        'date': None,
        'time': '',
        'area': 'JU',
        'tested': None,
        'confirmed': None,
        'hospitalized': None,
        'icu': None,
        'vent': None,
        'released': None,
        'deceased': None,
        'source': 'https://www.jura.ch/fr/Autorites/Coronavirus/Accueil/Coronavirus-Informations-officielles-a-la-population-jurassienne.html',
    }

    # parse number of confirmed cases
    table = soup.find("h3", string=re.compile("Cas .*infection au coronavirus COVID-19 .*canton .*Jura")).parent.find("table")

    (confirmed_cell, date_cell) = table.find_all('td')
    data['confirmed'] = int(confirmed_cell.find('p').string)

    # parse date
    datetime_match = re.search('Situation (.*) \((\d+)h\)', date_cell.string)
    update_datetime = dateparser.parse(
        datetime_match.group(1),
        languages=['fr']
    )
    data['date'] = update_datetime.date().isoformat()
    data['time'] = '%s:00' % datetime_match.group(2)

    c = conn.cursor()

    try:
        print(data)
        c.execute(
            '''
            INSERT INTO data (
                date,
                time,
                abbreviation_canton_and_fl,
                ncumul_tested,
                ncumul_conf,
                ncumul_hosp,
                ncumul_ICU,
                ncumul_vent,
                ncumul_released,
                ncumul_deceased,
                source
            )
            VALUES
            (?,?,?,?,?,?,?,?,?,?,?)
            ''',
            [
                data['date'],
                data['time'],
                data['area'],
                data['tested'],
                data['confirmed'],
                data['hospitalized'],
                data['icu'],
                data['vent'],
                data['released'],
                data['deceased'],
                data['source'],
            ]
        )
    except sqlite3.IntegrityError:
        print("Error: Data for this date + time has already been added")
    finally:
        conn.commit()
    

# canton bern - start url
start_url = 'https://www.jura.ch/fr/Autorites/Coronavirus/Accueil/Coronavirus-Informations-officielles-a-la-population-jurassienne.html'

# get page with data on it
page = requests.get(start_url)
soup = BeautifulSoup(page.content, 'html.parser')

try:
    parse_page(soup, conn)
except Exception as e:
    print("Error: %s" % e)
    print(traceback.format_exc())
    raise
finally:
    conn.close()


# trigger GitHub Action API
if 'MORPH_GH_USER' in os.environ:
    gh_user = os.environ['MORPH_GH_USER']
    gh_token = os.environ['MORPH_GH_TOKEN']
    gh_repo = os.environ['MORPH_GH_REPO']

    url = 'https://api.github.com/repos/%s/dispatches' % gh_repo
    payload = {"event_type": "update"}
    headers = {'content-type': 'application/json'}
    r = requests.post(url, data=json.dumps(payload), headers=headers, auth=(gh_user, gh_token))
    print(r)

