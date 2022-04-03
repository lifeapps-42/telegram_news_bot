import os
import http
import logging

from flask import Flask, request
from werkzeug.wrappers import Response

from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Filters, MessageHandler, CommandHandler, CallbackContext, Updater, ConversationHandler

app = Flask(__name__)

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

logger = logging.getLogger(__name__)

WAITING_POST, POST_ADDED = range(2)

global user_suggestion

news_suggestion_bucket = "@pupik_news"


def start(update: Update, context: CallbackContext) -> None:
    update.message.reply_text(
        'Добро пожаловать! Чтобы предложить новость, нажите /news')


def news_flow_start(update: Update, context: CallbackContext) -> int:
    update.message.reply_text(
        'Теперь напишите вашу новость, а затем нажмите Отправить')
    return WAITING_POST


def store_post(update: Update, context: CallbackContext) -> int:
    global user_suggestion
    user_suggestion = update.message
    reply_keyboard = [['Отправить', 'Отменить']]
    update.message.reply_text(
        'Хорошо! Если готовы отправить эту новость, нажмите Кнопку Отправить',
        reply_markup=ReplyKeyboardMarkup(
            reply_keyboard, one_time_keyboard=True, input_field_placeholder='Отправляем?', resize_keyboard=True
        ),
    )
    return POST_ADDED


def cancel_submitting(update: Update, context: CallbackContext) -> int:
    global user_suggestion
    user_suggestion = None
    update.message.reply_text('Ну тогда в другой раз :)')
    return ConversationHandler.END


def submit_post(update: Update, context: CallbackContext) -> int:
    global user_suggestion
    message = user_suggestion
    context.bot.forward_message(chat_id=news_suggestion_bucket,
                                from_chat_id=message.chat_id, message_id=message.message_id)
    update.message.reply_text(
        'Новость отправлена на модерацию, спасибо!', reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END


def cancel_conv(update: Update, context: CallbackContext) -> int:
    global user_suggestion
    message = user_suggestion
    context.bot.forward_message(chat_id=news_suggestion_bucket,
                                from_chat_id=message.chat_id, message_id=message.message_id)
    update.message.reply_text('Новость отправлена на модерацию, спасибо!')
    return ConversationHandler.END


bot_token = os.environ["TOKEN"]
updater = Updater(token=bot_token, use_context=True)
dispatcher = updater.dispatcher
start_handler = CommandHandler('start', start)
cancel_handler = CommandHandler('cancel', cancel_submitting)
news_flow_start_handler = CommandHandler('news', news_flow_start)
store_post_handler = MessageHandler(Filters.all, store_post)
submit_handler = MessageHandler(
    Filters.regex('^(Отправить)$'), submit_post)
cancel_submit_handler = MessageHandler(
    Filters.regex('^(Отменить)$'), cancel_submitting)

news_flow_conversation_handler = ConversationHandler(

    entry_points=[news_flow_start_handler],
    states={
        WAITING_POST: [store_post_handler],
        POST_ADDED: [submit_handler, cancel_submit_handler],
    },
    fallbacks=[cancel_handler],
)

dispatcher.add_handler(start_handler)
dispatcher.add_handler(news_flow_conversation_handler)


@app.post('/')
def index():
    updater.start_polling()


if __name__ == '__main__':
    server_port = os.environ.get('PORT', '8080')
    app.run(debug=False, port=server_port, host='0.0.0.0')
