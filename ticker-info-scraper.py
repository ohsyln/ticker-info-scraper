from bs4 import BeautifulSoup
import datetime
import json
import logger
import requests
import time

from user_agent import generate_user_agent

log = logger.Log(__file__)

CHAT_ID = 'chat_id'
TICKER = 'ticker'
TICKERS = 'tickers'
SHORT_INTEREST = 'short_interest'
PUB_FLOAT = 'pub_float'
PREMARKET_VOL = 'premarket_vol'
DILUTION = 'dilution'
CHART = 'chart'
FINVIZ_URL = 'https://finviz.com/quote.ashx'
CHART_URL = 'https://finviz.com/quote.ashx?t={}'
MARKETWATCH_URL = 'https://marketwatch.com/investing/stock/{}'
OTCMARKETS_FILING_URL = 'https://www.otcmarkets.com/filing/html?id={coy_id}&guid={guid}'
NO_OF_FILING_ENTRIES = '20'
OTCMARKETS_URL = 'https://backend.otcmarkets.com/otcapi/company/sec-filings/{0}?symbol={0}&page=1&pageSize=' + NO_OF_FILING_ENTRIES
OFFERING_424 = '424'
QUARTER_10Q = '10-Q'
class ParsingException(Exception):
  pass
class Parser():
  def __init__(self):
    self.unknown = 'Unknown'
    pass
  # Crawls various sites and APIs for info about ticker 
  # Returns:
  #   dict of values
  def extract_info(self, ticker):
    short_interest = ''
    pub_float = ''
    premarket_vol = ''
    dilution = ''

    [short_interest, pub_float] = self.get_SI_float_from_finviz(ticker)
    premarket_vol = self.get_pre_vol_from_marketwatch(ticker)
    dilution = self.get_dilution_from_otcmarkets(ticker)
    chart_url = CHART_URL.format(ticker)

    return {
      TICKER: ticker.upper(),
      SHORT_INTEREST: short_interest,
      PUB_FLOAT: pub_float,
      PREMARKET_VOL: premarket_vol,
      DILUTION: dilution,
      CHART: chart_url
    }

  # Helper method used by get_SI_float_from_finviz()
  def strip_finviz_str(self, s):
    s = str(s)
    s = s.split('">')[-1]
    s = s.split('</')[0]
    s = s.split('>')[-1]
    return s

  # Retrieves pub_float and short_interest from finviz.com
  # Returns:
  #   [short_interest, pub_float]
  def get_SI_float_from_finviz(self, ticker):
    [short_interest, pub_float] = self.unknown, self.unknown

    r = requests.get(url=FINVIZ_URL, params={'t': ticker}, headers={'User-Agent': generate_user_agent()})

    if r.status_code != 200:
      print('get_SI_float_from_finviz (requests.get):')
      print('  code: {}, ticker: {}'.format(r.status_code, ticker))
      return [short_interest, pub_float]

    soup = BeautifulSoup(r.content, 'html.parser')
    tds = soup.find_all('td')
    for i, td in enumerate(tds):
      try:
        if "Shs Float" in td.contents:
          pub_float = tds[i+1].contents
          pub_float = self.strip_finviz_str(pub_float)
      except:
        raise ParsingException("parsing error: can't find tds[i+1] pub_float info")

      try:
        if "Short Float" in td.contents:
          short_interest = tds[i+1].contents
          short_interest = self.strip_finviz_str(short_interest)
      except:
        raise ParsingException("parsing error: can't find tds[i+1] short_interest info")

    return [short_interest, pub_float]

  def strip_marketwatch_str(self, s):
    s = str(s)
    s = ''.join(s.strip('</bg-quote>]'))
    s = s.split('">')[-1]
    return s

  # Retrieves premarket_vol from MarketWatch
  # Returns:
  #   premarket_vol
  def get_pre_vol_from_marketwatch(self, ticker):
    premarket_vol = self.unknown

    try:
      r = requests.get(url=MARKETWATCH_URL.format(ticker), params={'mod': 'quote_search'})
    except Exception as e:
      print('{}: (requests.get)'.format(e))
      return premarket_vol
    else:
      if r.status_code != 200:
        print('get_pre_vol_from_marketwatch (requests.get)')
        print('code: {}, ticker: {}'.format(r.status_code, ticker))
        return premarket_vol

    soup = BeautifulSoup(r.content, 'html.parser')
    tds = soup.find_all('span')
    for i, td in enumerate(tds):
      try:
        if "Premarket Volume:" in td.contents:
          premarket_vol = self.strip_marketwatch_str(tds[i+1].contents)
      except:
        raise ParsingException("parsing error: can't find tds[i+1] pub_float info")

    return premarket_vol

  # Retrieves dilution from otcmarkets.com
  # Returns:
  #   dict of filing urls with keys '424' and '10-Q'
  def get_dilution_from_otcmarkets(self, ticker):
    url_list = {OFFERING_424: [], QUARTER_10Q: []}
    
    # Error-checking for requests
    try:
      r = requests.get(url=OTCMARKETS_URL.format(ticker))
    except Exception as e:
      print('{}: (requests.get)'.format(e))
      return self.format(urllist(url_list)) 
    else:
      if r.status_code != 200:
        print('get_dilution_from_otcmarkets (requests.get)')
        print('code: {}, ticker: {}'.format(r.status_code, ticker))
        return self.format(urllist(url_list)) 

    j = r.json()
    try:
      records = j['records']
    except:
      raise ParsingException("(get_dilution_from_otcmarkets) can't find 'records' key in JSON")
      return self.format(urllist(url_list))

    found_10Q = 0
    # TODO consider doing automated dilution analysis via filing_url
    for record in records:
      try:
        if OFFERING_424 in record['formType']:
          received_date = record['receivedDate']
          received_date = self.epoch_to_datetime(received_date)
          coy_id = record['id']
          guid = record['guid'][16:31]
          filing_url = OTCMARKETS_FILING_URL.format(coy_id=coy_id, guid=guid)
          msg = '({}) {}'.format(received_date, filing_url)
          url_list[OFFERING_424].append(msg)
        if QUARTER_10Q in record['formType'] and not found_10Q:
          received_date = record['receivedDate']
          received_date = self.epoch_to_datetime(received_date)
          coy_id = record['id']
          guid = record['guid'][16:31]
          filing_url = OTCMARKETS_FILING_URL.format(coy_id=coy_id, guid=guid)
          msg = '({}) {}'.format(received_date, filing_url)
          url_list[QUARTER_10Q].append(msg)
          found_10Q = 1
      except:
        raise ParsingException('error when parsing JSON record')

    return self.format_urllist(url_list)

  # Helper method to convert EPOCH to readable date time
  def epoch_to_datetime(self, dd):
    dd = int(str(dd)[:-3])
    return datetime.datetime.fromtimestamp(dd).strftime('%d/%m/%Y')

  # Helper method used by get_dilution_from_otcmarkets()
  # Formats dict into readable msg for Telegram 
  def format_urllist(self, url_list):
    msg = ''
    for k,v in url_list.items():
      if len(v) == 0:
        continue
      msg += '{}\n'.format(k)
      msg += '\n'.join(v)
      msg += '\n'

    if msg == '':
      msg = 'No 424* or 10-Qs found in first {} entries'.format(NO_OF_FILING_ENTRIES)

    return msg

############ TELEGRAM BOT ############
API_KEY = "<YOUR TELEGRAM BOT API KEY HERE>"
API_PREFIX = 'https://api.telegram.org/bot'
API_SEND = '/sendMessage'
API_GET = '/getUpdates'
class TelegramAPI():
  def __init__(self):
    self.prev_input = ''

  # Polls Telegram to await user inputs
  # Returns tickers, chat_id
  def poll_message(self):
    # Wait for reply
    not_success = 1
    URL = API_PREFIX + API_KEY + API_GET
    while not_success:
      try:
        r = requests.get(url=URL)
        output = self.parse_response(r)
      except requests.exceptions.RequestException as e:
        log.plog("RequestException: {} (retry in 60s)")
        time.sleep(60)
      else:
        # If tickers exist, we proceed
        if output[TICKERS]:
          not_success = 0
        else:
          #print("Waiting for user input..")
          time.sleep(2)

    self.prev_input = output[TICKERS]

    return output

  # Parse JSON response from user
  # Returns none if no polls from user via Telegram,
  # else returns [user_input, chat_id]
  def parse_response(self, r):
    output = {TICKERS: None, CHAT_ID: None}
    j = json.loads(r.text)
    msg_list = j["result"]
    try:
      output[TICKERS] = msg_list[-1]["message"]["text"]
    except:
      raise ParsingException("can't parse input from user: {}".format(msg_list[-1])) 
    try:
      output[CHAT_ID] = msg_list[-1]["message"]["from"]["id"]
    except:
      raise ParsingException("can't parse chat_id from user: {}".format(msg_list[-1])) 
    # Check if user polls for new info
    if output[TICKERS] == self.prev_input:
      return {TICKERS: None, CHAT_ID: None} 
    return output

  # Sends msg to user via Telegram bot
  def output(self, msg, chat_id):
    not_success = 1
    URL = API_PREFIX + API_KEY + API_SEND
    PARAMS = {'chat_id': chat_id, 'text': msg}
    while not_success:
      try:
        r = requests.get(url=URL, params=PARAMS)
      except requests.exceptions.RequestException as e:
        log.plog("RequestException: {} (retry in 60s)")
        time.sleep(60)
      else:
        # Successfully sent msg to user
        not_success = 0

############# FORMATTER ####################
class Formatter():
  def __init__(self):
    self.msg = ''
  def convert_to_message(self, info):
    self.msg = ''
    self.msg += '({})\n'.format(logger.now())
    self.msg += 'Ticker: {}\n'.format(info[TICKER])
    self.msg += 'Public Float: {}\n'.format(info[PUB_FLOAT])
    self.msg += 'Short Interest: {}\n'.format(info[SHORT_INTEREST])
    self.msg += 'Premarket Vol: {}\n'.format(info[PREMARKET_VOL])
    self.msg += 'Filings: \n{}\n'.format(info[DILUTION])
    self.msg += 'Chart URL: {}\n'.format(info[CHART])
    return self.msg

################## MAIN ####################
def main():
  parser = Parser()
  formatter = Formatter()
  telegram = TelegramAPI()

  while 1:
    # Polls user input via Telegram bot
    polled_output = telegram.poll_message()
    # Checks if both TICKERS and CHAT_ID are populated
    if not polled_output[TICKERS] or not polled_output[CHAT_ID]:
      continue

    # Converts comma-separated string to list of tickers
    ticker_list = (''.join(polled_output[TICKERS].split())).split(',')

    for ticker in ticker_list:
      # Extract info from ticker
      info = parser.extract_info(ticker)

      # Convert info into a Telegram text message
      msg = formatter.convert_to_message(info)

      # Send message via Telegram bot
      telegram.output(msg=msg, chat_id=polled_output[CHAT_ID])

if __name__=="__main__":
  main()
