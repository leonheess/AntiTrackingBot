import daemon
import os
import requests
import dotenv
import telebot
from datetime import datetime

START = 'Hello there! 😊 Send any link, and I try my best to remove all tracking from the link you sent. Give it a try!'
HELP = 'Send any link, and I try my best to remove all tracking from the link you sent 😊'
INVALID = 'That doesn\'t look like a link to me 🤔'
UNREACHABLE = 'Unfortunately, the link you sent me is not reachable 😔'
ERROR = 'Unfortunately, an unknown error occurred 😔'
NOCOPY = 'Unfortunately, I couldn\'t create a copyable URL because Telegram doesn\'t like some characters in the URL 🙄'

IMPOSSIBLE_URLS = ['https://open.spotify.com', 'https://www.instagram.com']
TELEGRAM_BREAKING_CHARS = ['_', '*', '[', ']']

def get_destination_url(url):
  return (requests.head(
    url,
    allow_redirects=True,
    headers={
      'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) CriOS/94.0.4606.52 Mobile/15E148 Safari/604.1'},
  )).url

with daemon.DaemonContext():
  dotenv.load_dotenv()
  bot = telebot.TeleBot(os.getenv('API_KEY'))

  @bot.message_handler(commands=['start'])
  def send_start(message):
    bot.reply_to(message, START)

  @bot.message_handler(commands=['help'])
  def send_help(message):
    bot.reply_to(message, HELP)

  @bot.message_handler(func=lambda message: True)
  def echo_all(message):
    text = message.text.strip()
    url_is_copyable = False

    if ' ' in text or '.' not in text:
      reply = INVALID
    else:
      try:
        if any(text.startswith(url) for url in IMPOSSIBLE_URLS):
          url = text
        else:
          text = text if text.startswith('http') else 'http://' + text
          url = get_destination_url(text)

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
      except requests.exceptions.MissingSchema:
        reply = INVALID
      except requests.ConnectionError:
        reply = UNREACHABLE
      except BaseException:
        reply = ERROR

    try:
      if url_is_copyable:
        bot.reply_to(message, reply, disable_web_page_preview=True, parse_mode='Markdown')
      else:
        bot.reply_to(message, reply, disable_web_page_preview=True)
    except BaseException:
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
