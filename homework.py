import os
import sys
import logging
import time
import telegram
import requests
from dotenv import load_dotenv


load_dotenv()


PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
# Повторный запрос проводится каждые 10 минут
RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def check_tokens():
    """Проверка токенов."""
    return all([PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID])


def send_message(bot, message):
    """Отправка сообщений."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logging.debug(message)
    except telegram.TelegramError:
        logging.error(message)


def get_api_answer(timestamp):
    """Запрос к API и получение ответа в формате JSON."""
    params = {'from_date': timestamp}
    try:
        response = requests.get(
            url=ENDPOINT,
            headers=HEADERS,
            params=params
        )
    except Exception:
        logging.error('Ошибка API')
    if response.status_code != 200:
        raise ValueError(response.status_code)
    try:
        return response.json()
    except ValueError:
        logging.error('Ошибка парсинга json')
        raise ValueError('Ошибка парсинга json')


def check_response(response):
    """Проверка полученных данных."""
    if not isinstance(response, dict):
        raise TypeError('Должен быть словарь')
    elif 'homeworks' not in response:
        raise Exception('Ошибка ключа')
    elif not isinstance(response['homeworks'], list):
        raise TypeError('Должен быть список')
    return response.get('homeworks')


def parse_status(homework):
    """Информация о статусе работы."""
    homework_status = homework.get('status')
    if (not isinstance(homework, dict)
            or 'status' not in homework
            or homework_status not in HOMEWORK_VERDICTS):
        logging.error(TypeError)
        raise TypeError('Ошибка данных')
    if 'homework_name' not in homework:
        logging.error(TypeError)
        raise TypeError('Ошибка данных')
    homework_name = homework.get('homework_name')
    verdict = HOMEWORK_VERDICTS[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        logging.critical('Error')
        sys.exit()
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    last_error = ''
    send_message(bot, 'Бот включился')
    while True:
        try:
            response = get_api_answer(timestamp)
            timestamp = response.get('current_date')
            homework = check_response(response)
            if homework:
                current_homework = homework[0]
                lesson_name = current_homework['lesson_name']
                homework_status = parse_status(current_homework)
                send_message(bot, lesson_name, homework_status)
            else:
                logging.debug('Нет статуса')
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logging.error(message)
            if message != last_error:
                send_message(bot, HOMEWORK_VERDICTS)
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)
    formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s'
    )
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    main()
