import os
import requests
import daemon
import dotenv
import telebot
from datetime import datetime

START = 'Hello there! 😊 Send any link, and I try my best to remove all tracking from the link you sent. Give it a try!'
HELP = 'Send any link, and I try my best to remove all tracking from the link you sent 😊'
INVALID = 'That doesn\'t look like a link to me 🤔'
UNREACHABLE = 'Unfortunately, the link you sent me is not reachable 😔'
ERROR = 'Unfortunately, an unknown error occurred 😔'

def get_destination_url(url):
  return (requests.head(
    url,
    allow_redirects=True,
    headers={"User-Agent": "Mozilla/5.0 (Linux; Android 11; SM-A102U) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.72 Mobile Safari/537.36"},
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
    reply = ERROR

    if ' ' in text or '.' not in text:
      reply = INVALID
    else:
      try:
        if text.startswith('https://open.spotify.com') or text.startswith('https://www.instagram.com'):
          url = text
        else:
          text = text if text.startswith('http') else 'http://' + text
          url = get_destination_url(text)

        if url.startswith('https://www.amazon'):
          url = url.split('/ref')[0]
        elif 'youtube.com' in url:
          url = 'https://m.youtube.com/watch?v=' + text.split('/')[3]
        else:
          url = url.split('?')[0]

        url = url[:-1] if url.endswith('/') else url
        reply = f'{url}\n\nTap here to copy: `{url}`'
      except requests.exceptions.MissingSchema:
        reply = INVALID
      except requests.ConnectionError:
        reply = UNREACHABLE
      except BaseException:
        reply = ERROR

    bot.reply_to(message, reply, disable_web_page_preview=True, parse_mode='Markdown')

    if str(message.chat.id) != os.getenv('USER_ID'):
      date = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
      bot.send_message(os.getenv('LOG_ID'), f'*Time:* {date}\n\n*Message:* `{text}`\n\n*Response:* {reply}', disable_web_page_preview=True, parse_mode='Markdown')

  bot.polling()