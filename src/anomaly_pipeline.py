import psycopg2 as pg2
from urllib.parse import quote_plus as url
import steam.webauth as wa
import os
import ast
import sys
import pickle
from src.market_to_mongo import *
from datetime import datetime, timedelta


class AnomalyPipeline:
    def __init__(self, last_date=datetime.utcnow().date()-timedelta(32)):
        self.last_date = last_date
        self.anomalies = None

    def update_database(self):
        conn = pg2.connect(dbname='steam_capstone', host='localhost')
        cur = conn.cursor()
        update_list = get_updatable_items(self.last_date, cur)
        session = login_to_steam()

        for item in update_list:
            update_entry(item, self.last_date, session, cur)
        pass

    def update_dataframe(self):
        pass

    def fit_anomalies(self):
        pass

def login_to_steam():
    user = wa.WebAuth(os.environ['STEAM_ID'], os.environ["STEAM_PASSWORD"])
    return user.login()

def get_updatable_items(date, cursor):
    """
    Looks through the Postgres database to see which items are missing up to date records.
    :param date: datetime.date() object of the latest date to request records for
    :param cursor: psql cursor
    :return: list of item names to request updates for
    """
    item_names = cursor.execute('select distinct(item_name) from sales where date > %(date)s;',
                                {'date': date}).fetchall()
    return [x[0] for x in item_names]

def update_entry(item_name, last_date, session, cursor):
    """
    Gets the latest entry of the item, requests data from Steam, then adds all of the missing price points between the
    latest entry and the last_date parameter.
    :param item_name: name of the item
    :param last_date: most recent entry to update database with
    :param session: Steam login session
    :param cursor: psql cursor
    :return: None
    """
    cursor.execute(
        """select item_id, date from sales
        where item_name = %(item_name)s
        order by date desc
        limit 1;""", {'item_name':item_name})
    item_id, latest_entry = cursor.fetchone()
    request = get_market_page(session, 730, item_name)

    # add in checks to make sure request worked
    price_history = request.json()['prices']
    if datetime.strptime(price_history[-1][0][:11], '%b %d %Y').date() != last_date:
        price_history.append([last_date.strftime('%b %d %Y 01: +0'), '0', '0'])
    # could fill in every missing date with 0's
    
    updates = [(item_id, item_name, datetime.strptime(date[:11], '%b %d %Y').date(), float(price), int(quantity))
               for date, price, quantity in price_history
               if last_date > datetime.strptime(date[:11], '%b %d %Y').date() >= latest_entry]


    pass
