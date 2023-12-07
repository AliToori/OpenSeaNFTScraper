#!/usr/bin/env python3
"""
    *******************************************************************************************
    OpenSeaBot:  OpenSea NFT Address and Price Scraper
    Author: Ali Toori, Python Developer
    *******************************************************************************************
"""
import json
import logging.config
import os
import pickle
import random
from datetime import datetime
from multiprocessing import freeze_support
from pathlib import Path
from time import sleep
import concurrent.futures

import pandas as pd
import pyfiglet
from selenium import webdriver
from selenium.common.exceptions import WebDriverException
from selenium.webdriver import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


class OpenSeaBot:
    def __init__(self):
        self.PROJECT_ROOT = Path(os.path.abspath(os.path.dirname(__file__)))
        self.file_settings = str(self.PROJECT_ROOT / 'BotRes/Settings.json')
        self.file_addresses = self.PROJECT_ROOT / 'BotRes/Addresses.csv'
        self.file_valid = self.PROJECT_ROOT / 'BotRes/Valid.csv'
        self.OPENSEA_HOME_URL = "https://opensea.io/"
        self.settings = self.get_settings()
        self.LOGGER = self.get_logger()
        self.driver = None

    # Get self.LOGGER
    @staticmethod
    def get_logger():
        """
        Get logger file handler
        :return: LOGGER
        """
        logging.config.dictConfig({
            "version": 1,
            "disable_existing_loggers": False,
            'formatters': {
                'colored': {
                    '()': 'colorlog.ColoredFormatter',  # colored output
                    # --> %(log_color)s is very important, that's what colors the line
                    'format': '[%(asctime)s,%(lineno)s] %(log_color)s[%(message)s]',
                    'log_colors': {
                        'DEBUG': 'green',
                        'INFO': 'cyan',
                        'WARNING': 'yellow',
                        'ERROR': 'red',
                        'CRITICAL': 'bold_red',
                    },
                },
                'simple': {
                    'format': '[%(asctime)s,%(lineno)s] [%(message)s]',
                },
            },
            "handlers": {
                "console": {
                    "class": "colorlog.StreamHandler",
                    "level": "INFO",
                    "formatter": "colored",
                    "stream": "ext://sys.stdout"
                },
                "file": {
                    "class": "logging.handlers.RotatingFileHandler",
                    "level": "INFO",
                    "formatter": "simple",
                    "filename": "OpenSeaBot.log",
                    "maxBytes": 5 * 1024 * 1024,
                    "backupCount": 3
                },
            },
            "root": {"level": "INFO",
                     "handlers": ["console", "file"]
                     }
        })
        return logging.getLogger()

    @staticmethod
    def enable_cmd_colors():
        # Enables Windows New ANSI Support for Colored Printing on CMD
        from sys import platform
        if platform == "win32":
            import ctypes
            kernel32 = ctypes.windll.kernel32
            kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)

    @staticmethod
    def banner():
        pyfiglet.print_figlet(text='____________ OpenSeaBot\n', colors='RED')
        print('Author: AliToori, Full-Stack Python Developer\n'
              'Website: https://boteaz.com\n'
              '************************************************************************')

    def get_settings(self):
        """
        Creates default or loads existing settings file.
        :return: settings
        """
        if os.path.isfile(self.file_settings):
            with open(self.file_settings, 'r') as f:
                settings = json.load(f)
            return settings
        settings = {"Settings": {
            "ThreadsCount": 5
        }}
        with open(self.file_settings, 'w') as f:
            json.dump(settings, f, indent=4)
        with open(self.file_settings, 'r') as f:
            settings = json.load(f)
        return settings

    # Get random user-agent
    def get_user_agent(self):
        file_uagents = self.PROJECT_ROOT / 'BotRes/user_agents.txt'
        with open(file_uagents) as f:
            content = f.readlines()
        u_agents_list = [x.strip() for x in content]
        return random.choice(u_agents_list)

    # Get random user-agent
    def get_proxy(self):
        file_proxies = self.PROJECT_ROOT / 'BotRes/proxies.txt'
        with open(file_proxies) as f:
            content = f.readlines()
        proxy_list = [x.strip() for x in content]
        proxy = random.choice(proxy_list)
        self.LOGGER.info(f'Proxy selected: {proxy}')
        return proxy

    # Get web driver
    def get_driver(self, proxy=False, headless=False):
        driver_bin = str(self.PROJECT_ROOT / "BotRes/bin/chromedriver.exe")
        service = Service(executable_path=driver_bin)
        options = webdriver.ChromeOptions()
        options.add_argument("--start-maximized")
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-notifications")
        options.add_argument("--disable-blink-features")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-gpu")
        options.add_argument("--dns-prefetch-disable")
        options.add_argument('--ignore-ssl-errors')
        options.add_argument('--ignore-certificate-errors')
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option('excludeSwitches', ['enable-logging'])
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        prefs = {"profile.default_content_setting_values.geolocation": 2,
                 "profile.managed_default_content_setting_values.images": 2}
        options.add_experimental_option("prefs", prefs)
        options.add_argument(F'--user-agent={self.get_user_agent()}')
        if proxy:
            options.add_argument(f"--proxy-server={self.get_proxy()}")
        if headless:
            options.add_argument('--headless')
        driver = webdriver.Chrome(service=service, options=options)
        return driver

    # Finish and quit browser
    def finish(self, driver):
        try:
            self.LOGGER.info(f'Closing browser')
            driver.close()
            driver.quit()
        except WebDriverException as exc:
            self.LOGGER.info(f'Issue while closing browser: {exc.args}')

    @staticmethod
    def wait_until_visible(driver, css_selector=None, element_id=None, name=None, class_name=None, tag_name=None, duration=10000, frequency=0.01):
        if css_selector:
            WebDriverWait(driver, duration, frequency).until(EC.visibility_of_element_located((By.CSS_SELECTOR, css_selector)))
        elif element_id:
            WebDriverWait(driver, duration, frequency).until(EC.visibility_of_element_located((By.ID, element_id)))
        elif name:
            WebDriverWait(driver, duration, frequency).until(EC.visibility_of_element_located((By.NAME, name)))
        elif class_name:
            WebDriverWait(driver, duration, frequency).until(
                EC.visibility_of_element_located((By.CLASS_NAME, class_name)))
        elif tag_name:
            WebDriverWait(driver, duration, frequency).until(EC.visibility_of_element_located((By.TAG_NAME, tag_name)))

    def get_address_details(self, addresses):
        url_filter = '?search[sortBy]=UNIT_PRICE&search[sortAscending]=false'
        # driver = self.get_driver(proxy=True, headless=False)
        counter = 0
        for i, address in enumerate(addresses):
            counter += 1
            driver = self.get_driver(proxy=True, headless=False)
            # if counter >= 10:
            #     counter = 0
            #     self.finish(driver=driver)
            #     driver = self.get_driver(proxy=False, headless=False)
            final_url = self.OPENSEA_HOME_URL + address + url_filter
            self.LOGGER.info(f"Scraping stats of {i}: {address}, URL: {final_url}")
            # driver = self.get_driver(proxy=False, headless=False)
            driver.get(final_url)
            self.LOGGER.info(f"Waiting for OpenSea to load")
            collection, collection_name, best_offer, premium = '', '', '', ''
            # key = input(f'Enter a Key')
            # if key == 'n':
            #     continue
            try:
                self.wait_until_visible(driver=driver, css_selector='[class="sc-29427738-0 sc-bdnxRM dKfiYh iIKkrq"]', duration=10)
                address_name = driver.find_element(By.CSS_SELECTOR, '[class="sc-29427738-0 sc-bdnxRM dKfiYh iIKkrq"]').text
                if 'Unnamed' not in address_name:
                    premium = 'Y'
            except:
                pass
            try:
                self.wait_until_visible(driver=driver, css_selector='[class="sc-1f719d57-0 fKAlPV Asset--anchor"]', duration=10)
            except:
                self.LOGGER.info(f"No collection found")
                continue
            try:
                collection = str(driver.find_element(By.CSS_SELECTOR, '[class="sc-29427738-0 sc-d0e902a1-3 sc-21df3ef5-6 sc-ec8f13a5-5 eLucQB hVPIAI kixOOB"]').text).replace('"', '')
            except:
                pass
            asset_url = driver.find_element(By.CSS_SELECTOR, '[class="sc-1f719d57-0 fKAlPV Asset--anchor"]').get_attribute('href')
            driver.get(asset_url)
            self.LOGGER.info(f"Waiting for stats to load")
            try:
                self.wait_until_visible(driver=driver, css_selector='[class="sc-1f719d57-0 fKAlPV CollectionLink--link"]', duration=5)
            except:
                continue
            try:
                collection_name = str(driver.find_element(By.CSS_SELECTOR, '[class="sc-1f719d57-0 fKAlPV CollectionLink--link"]').text)
            except:
                pass
            try:
                best_offer = driver.find_element(By.CSS_SELECTOR, '[class="sc-1a668f09-0 UitxP Price--fiat-amount Price--fiat-amount-secondary"]').text
            except:
                pass
            asset_number = asset_url.split('/')[-1]
            stats = {"TodaysDate": datetime.now().strftime("%m-%d-%Y"), "ScanAddress": address, "CollectionName": collection_name,
                     "Collection": collection, "AssetNumber": asset_number, "BestOffer": best_offer, "Premium": premium}
            self.LOGGER.info(f'Stats: {str(stats)}')
            df_following = pd.DataFrame([stats])
            # if file does not exist write headers
            if not os.path.isfile(self.file_valid):
                df_following.to_csv(self.file_valid, index=False, sep='|')
            else:  # else if exists so append without writing the header
                df_following.to_csv(self.file_valid, mode='a', header=False, index=False, sep='|')
            self.LOGGER.info(f"Stats have been saved to {self.file_valid}")
            self.finish(driver=driver)

    def main(self):
        freeze_support()
        self.enable_cmd_colors()
        self.banner()
        self.LOGGER.info(f'OpenSeaBot launched')
        thread_counts = self.settings["Settings"]["ThreadCount"]
        addresses = pd.read_csv(self.file_addresses, index_col=None)
        addresses = [address["Address"] for address in addresses.iloc]
        self.get_address_details(addresses)
        # chunk = round(len(addresses) / thread_counts)
        # address_chunks = [addresses[x:x + chunk] for x in range(len(addresses))]
        # with concurrent.futures.ThreadPoolExecutor(max_workers=thread_counts) as executor:
        #     executor.map(self.get_address_details, address_chunks)
        # self.LOGGER.info(f'Process completed successfully!')


if __name__ == '__main__':
    OpenSeaBot().main()
