import pandas as pd
import telebot
import requests
import dbworker
import config
import os
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.support.ui import Select
from matplotlib import pyplot as plt
import matplotlib.ticker as ticker

bot = telebot.TeleBot(config.token)

ccy_code_dict = {
    'USD': 52148,
    'EUR': 52170,
    'GBP': 52146,
    'CHF': 52133,
    'AUD': 52182,
    'BRL': 52174,
    'KRW': 52073,
    'HKD': 52235,
    'INR': 52238,
    'KZT': 52247,
    'CAD': 52202,
    'CNY': 52207,
    'SGD': 52122,
    'TRY': 52158,
    'SEK': 52132,
    'ZAR': 52127,
    'JPY': 52246
}

def init_date_to_bd_bm_by(my_date):
    bd = str(int(my_date[:2]))
    bm = int(my_date[3:5])-1
    by = str(int(my_date[6:]))
    return bd,bm,by

def get_stat_from_finmarket(currency, initial_date):
    bd, bm, by = init_date_to_bd_bm_by(initial_date)
    driver = webdriver.Chrome()  # 'C:/Users/chromedriver.exe'
    driver.get("http://www.finmarket.ru/currency/rates/?id=10148&pv=1#archive")
    # находим форму для ввода даты
    fld = driver.find_element_by_xpath(
        "/html/body/div[6]/div[7]/div[2]/div[7]/div[7]/form/table/tbody/tr[1]/td[1]/select")
    fld.click()
    select = Select(driver.find_element_by_name('cur'))
    select.select_by_value(str(ccy_code_dict[currency.upper().strip()]))

    # устанавливаем начальную дату
    select = Select(driver.find_element_by_name('bd'))  # день
    select.select_by_value(bd)
    select = Select(driver.find_element_by_name('bm'))  # месяц
    select.select_by_index(bm)
    select = Select(driver.find_element_by_name('by'))  # год
    select.select_by_value(by)

    # находим input и нажимаем
    fld = driver.find_element_by_xpath(
        "/html/body/div[6]/div[7]/div[2]/div[7]/div[7]/form/table/tbody/tr[2]/td[4]/input")
    fld.click()
    # забираем данные со страницы для парсинга, первоначально ждем, чтобы страница прогрузилась.
    driver.implicitly_wait(4)
    # загружаем данные по странице и используем супчик
    response = driver.page_source
    obj = BeautifulSoup(response, 'lxml')
    try: # если 4 сек не хватило для загрузки страницы, то возникнет ошибка при обращении к элементу массива
        my_table = obj.find_all('table', {'class': 'karramba'})[0]
    except Exception: # здесь мы подождем еще 10 сек и снова сделаем поиск на странице
        driver.implicitly_wait(10)
        response = driver.page_source
        obj = BeautifulSoup(response, 'lxml')
        try:
            my_table = obj.find_all('table', {'class': 'karramba'})[0]
        except Exception: # если уж и сейчас ошибка при обращении к нулевому элементу массива, то выйдем из функции
            return "Error in Parsing"

    trs = my_table.find_all("tr")
    dates = []
    ccy_values = []
    for element in range(0, len(trs) - 1):
        if element != 0 and element!=len(trs)-1:
            tds = trs[element].find_all("td")
            dates.append(tds[0].text)
            ccy_values.append(float(tds[2].text.replace(',', '.')))
    driver.close()

    df = pd.DataFrame({'date': dates, 'CCY': ccy_values})
    x = df['date']
    y = df['CCY']
    fig, ax = plt.subplots()
    ax.plot(x, y)
    ax.xaxis.set_major_locator(ticker.MultipleLocator(df.shape[0] / 10))
    ax.grid(which='major', color='gray', linestyle=':')
    ax.tick_params(axis='x', which='major', labelcolor='black', labelbottom=True, labelrotation=45)
    ax.set_title(currency + '/RUB')
    fig.savefig(currency +'-'+ str(initial_date.replace('.','-')), dpi=fig.dpi, bbox_inches="tight")
    del df
    return 0

def date_check(current_date):
    if current_date[0] in [str(i) for i in range(0,4)]:
        if current_date[1] in [str(i) for i in range(0,10)]:
            if current_date[2] == '.':
                if int(current_date[:2]) in range(1, 32):
                    if current_date[3] in [str(i) for i in range(0,2)]:
                        if current_date[4] in [str(i) for i in range(0, 10)]:
                            if int(current_date[3:5]) in range(1, 13):
                                if current_date[5] == '.':
                                    if current_date[6:].isdigit():
                                        if int(current_date[6:]) in range(2010, 2021):
                                            return True

    return False

@bot.message_handler(commands=["commands"])
def cmd_commands(message):
    bot.send_message(message.chat.id, "/start - старт запроса графика инсотранной валюты.\n"
                                      "/reset - новый запрос графика валюты.\n"
                                      "/commands - список возможных команд.\n"
                                      "/currencies - список доступных валют для построения графика.")

@bot.message_handler(commands=["start"])
def cmd_start(message):
    dbworker.set_state(message.chat.id, dbworker.States.S_START.value)
    # удаляем записи из базы по идентификаторам
    dbworker.del_state(str(message.chat.id)+'ccy')
    dbworker.del_state(str(message.chat.id) + 'BEGIN_DAY')
    # Под "остальным" понимаем состояние "0" - начало диалога
    bot.send_message(message.chat.id, "Привет, это FX-бот, он поможет тебе получить график валюты. \n"
                                      "1) Сначала нужно выбрать и ввести валютную пару.\n"
                                      "Список валютных пар можно посмотреть через /currencies.\n"
                                      "2) После выбора валюты требуется указать начальную дату в формате \"ДД.ММ.ГГГГ\"\n"
                                      "Напечатав /commands, ты увидишь набор доступных команд.\n"
                                      "Для возврата в начало используй /reset.")

    dbworker.set_state(message.chat.id, dbworker.States.S_ENTER_CCY.value)


# По команде /reset будем сбрасывать состояния, возвращаясь к началу диалога
@bot.message_handler(commands=["reset"])
def cmd_reset(message):
    # удаляем записи из базы по идентификаторам
    dbworker.del_state(str(message.chat.id)+'ccy')
    dbworker.del_state(str(message.chat.id) + 'BEGIN_DAY')
    bot.send_message(message.chat.id, "Давай сделаем новый график.\n"
                                      "1) Сначала нужно выбрать и ввести валютную пару.\n"
                                      "2) Затем требуется указать начальную дату в формате \"ДД.ММ.ГГГГ\".\n"
                                      "Используй /currencies для вывода списка валют или /commands для поиска команд.")
    dbworker.set_state(message.chat.id, dbworker.States.S_ENTER_CCY.value)

@bot.message_handler(commands=["currencies"])
def cmd_currencies_list(message):
    bot.send_message(message.chat.id, ', '.join([e+'\n' if i%5 == 4 else e for i,e in enumerate(ccy_code_dict.keys())]).replace('\n,', ',\n'))

@bot.message_handler(func=lambda message: dbworker.get_current_state(message.chat.id) == dbworker.States.S_ENTER_CCY.value
                     and message.text.strip().lower() not in ('/reset', '/start', '/commands', '/currencies'))
def get_CCY(message):
    dbworker.del_state(str(message.chat.id)+'ccy') # Если в базе когда-то был CCY, удалим (мы же новый пишем)
    if message.text.upper().strip() in ccy_code_dict.keys():
        dbworker.set_state(str(message.chat.id) + 'ccy', message.text.upper().strip())
        bot.send_message(message.chat.id, "OK, ты выбрал валюту: " + message.text.upper() + "\n"
                                          "Теперь нужно указать начальную дату в формате \"ДД.ММ.ГГГГ\".\n"
                                          "Если ошибся, то жми /reset для запуска сначала.")
        dbworker.set_state(message.chat.id, dbworker.States.S_ENTER_BEGIN_DAY.value)
    else:
        bot.send_message(message.chat.id, "Либо валюта была введена с ошибками, либо её нет среди /currencies.\n"
                                          "Попробуй нажать /reset для запуска сначала.")

@bot.message_handler(func=lambda message: dbworker.get_current_state(message.chat.id) == dbworker.States.S_ENTER_BEGIN_DAY.value
                     and message.text.strip().lower() not in ('/reset', '/start', '/commands', '/currencies'))
def enter_the_day(message):

    dbworker.del_state(str(message.chat.id) + 'BEGIN_DAY')
    current_CCY = dbworker.get_current_state(str(message.chat.id)+'ccy')

    current_date = message.text.lower().strip()
    if date_check(current_date):
        dbworker.set_state(str(message.chat.id) + 'BEGIN_DAY', current_date)
        bot.send_message(message.chat.id, 'Cпасибо за запрос, я ищу необходимые данные. Подожди несколько секунд.\n')
        get_stat_from_finmarket(current_CCY, current_date)
        my_f = open(current_CCY+'-'+ str(current_date.replace('.','-'))+'.png', 'rb')
        # создаем словарь фото
        files = {'photo': my_f}
        # отправляем это фото через сервер телеграма
        requests.post('https://api.telegram.org/bot' + config.token + '/sendPhoto?chat_id={}'.format(message.chat.id),
                  files=files)
        # закрываем файл
        my_f.close()
        # удаляем файл
        os.remove(current_CCY+'-'+ str(current_date.replace('.','-'))+'.png')
        dbworker.set_state(message.chat.id, dbworker.States.S_START.value)
    else:
        bot.send_message(message.chat.id, "Дата была введена неверно, возможно год < 2010 или > 2020.\n"
                                          "Попробуй нажать /reset для запуска сначала.")





@bot.message_handler(func=lambda message: dbworker.get_current_state(message.chat.id) == dbworker.States.S_START.value and message.text.lower().strip() not in (
        '/reset',  '/start', '/commands',  '/currencies'))
def cmd_sample_message(message):
    bot.send_message(message.chat.id, "Привет. я - FX-bot!\n"
                                      "Я не особенно умен, но умею строить графики валют.\n"
                                      "Жми /start и мы начнем. \n")
    bot.send_photo(message.chat.id, 'https://cdn.vox-cdn.com/thumbor/GABGQ1H3qHJEoN0DL_tIyTSXYtM=/0x56:640x416/1600x900/cdn.vox-cdn.com/assets/3197731/FX_logo.jpg')


if __name__ == '__main__':
    bot.infinity_polling()
