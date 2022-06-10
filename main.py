import os
import requests
import dotenv
import telebot
import logging
import sys
from datetime import datetime
from torrequest import TorRequest

START = 'Hello there! 😊 Send any link, and I try my best to remove all tracking from the link you sent. Give it a try!'
HELP = 'Send any link, and I try my best to remove all tracking from the link you sent 😊'
INVALID = 'That doesn\'t look like a link to me 🤔'
UNREACHABLE = 'Unfortunately, the link you sent me is not reachable 😔'
ERROR = 'Unfortunately, an unknown error occurred 😔'
NOCOPY = 'Unfortunately, I couldn\'t create a copyable URL because Telegram doesn\'t like some characters in the URL 🙄'

IMPOSSIBLE_URLS = ['https://open.spotify.com', 'https://www.instagram.com']
SCRAPE_SHIELDED_URLS = ['https://vm.tiktok.com', 'https://tiktok.com']
TELEGRAM_BREAKING_CHARS = ['_', '*', '[', ']']
USER_AGENT = 'Mozilla/5.0 (iPhone; CPU iPhone OS 12_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148'
REQUEST_ARGS = { 'allow_redirects': True, 'headers': { 'User-Agent': USER_AGENT, 'Connection': 'keep-alive' }, 'timeout': 5 }

def getDespiteScrapeShield(url, retries):
  try:
    with TorRequest() as tr:
      tr.reset_identity()
      return tr.get(url, **REQUEST_ARGS).url
  except OSError:
    if retries > 0:
      logger.info('Using Tor failed. Retrying ' + str(6-retries) + ' of 5...')
      getDespiteScrapeShield(url, retries-1)
    else:
      raise requests.ConnectionError

logger = logging.getLogger('atb')
logger.setLevel(logging.INFO)
formatter = logging.Formatter(fmt='%(asctime)s %(name)s.%(levelname)s: %(message)s', datefmt='%Y.%m.%d %H:%M:%S')
handler = logging.StreamHandler(stream=sys.stdout)
handler.setFormatter(formatter)
logger.addHandler(handler)

logger.info('Logging online')

dotenv.load_dotenv()
bot = telebot.TeleBot(os.getenv('API_KEY'))

logger.info('Telegram bot online')

@bot.message_handler(commands=['start'])
def send_start(message):
  bot.reply_to(message, START)

@bot.message_handler(commands=['help'])
def send_help(message):
  bot.reply_to(message, HELP)

@bot.message_handler(func=lambda message: True)
def echo_all(message):
  text = message.text.strip()
  logger.info('New message: ' + text)
  url_is_copyable = False

  if ' ' in text or '.' not in text:
    reply = INVALID
  else:
    try:
      if any(text.startswith(url) for url in IMPOSSIBLE_URLS):
        url = text
      else:
        text = text if text.startswith('http') else 'http://' + text
        if any(text.startswith(url) for url in SCRAPE_SHIELDED_URLS):
          logger.info('Using Tor to circumvent scrape shield...')
          url = getDespiteScrapeShield(text, 5)
        else:
          url = (requests.get(text, **REQUEST_ARGS)).url

      logger.info('Destination URL determined to be ' + url)

      if url.startswith('https://www.amazon') and len(parts := url.split('/dp/')) >= 2:
        url = parts[0] + '/dp/' + parts[1][0:10]
      elif 'm.youtube.com' in url and len(parts := text.split('/')) >= 4:
        url = 'https://m.youtube.com/watch?v=' + parts[3]
      elif 'tiktok.com/@' in url and len(parts := url.split('/')) >= 6:
        url = 'https://m.tiktok.com/v/' + parts[5].split('?')[0] + '.html'
      elif 'google.com/search?q=' in url:
        url = url.split('&')[0]
      else:
        url = url.split('?')[0]

      formatted_url = url[:-1] if url.endswith('/') else url
      copy_text = f'Tap here to copy:\n\n`{formatted_url}`'
      url_is_copyable = not any(char in formatted_url for char in TELEGRAM_BREAKING_CHARS)
      reply = f'{formatted_url}\n\n\n{copy_text if url_is_copyable else NOCOPY}'

      logger.info('Final URL determined to be ' + formatted_url)
    except requests.exceptions.MissingSchema:
      logger.error('Invalid URL detected')
      reply = INVALID
    except (requests.ConnectionError, requests.Timeout):
      logger.error('URL could not be reached')
      reply = UNREACHABLE
    except BaseException as e:
      logger.error(e)
      reply = ERROR

  try:
    if url_is_copyable:
      bot.reply_to(message, reply, disable_web_page_preview=True, parse_mode='Markdown')
    else:
      bot.reply_to(message, reply, disable_web_page_preview=True)
  except BaseException as e:
    logger.error(e)
    bot.reply_to(message, ERROR)

  if str(message.chat.id) != os.getenv('USER_ID'):
    date = datetime.now().strftime('%d.%m.%Y %H:%M:%S')
    log_message = f'*Time:* {date}\n\n*Message:* `{text}`\n\n*Response:* {reply}'
    log_channel = os.getenv('LOG_ID')

    if url_is_copyable:
      bot.send_message(log_channel, log_message, disable_web_page_preview=True, parse_mode='Markdown')
    else:
      bot.send_message(log_channel, log_message.replace('*', '').replace('`', ''), disable_web_page_preview=True)

bot.polling()
