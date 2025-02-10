import datetime
import asyncio

from curl_cffi import requests
from config import CMC_API_KEY, TOKEN, CHAT_ID, loss

TG_URL = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
CMC_MAP_URL = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/map"
CMC_QUOTES_URL = "https://pro-api.coinmarketcap.com/v2/cryptocurrency/quotes/latest"

HEADERS = {
    "Accepts": "application/json",
    "X-CMC_PRO_API_KEY": CMC_API_KEY,
}

tokens = []

loss = -loss


async def fetch(url, params=None):
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, lambda: requests.get(url, headers=HEADERS, params=params))


async def get_crypto_info(token_name):
    response = await fetch(CMC_MAP_URL)
    if response.status_code == 200:
        data = response.json()
        for crypto in data["data"]:
            if crypto["name"].lower() == token_name.lower():
                return {"id": crypto["id"], "name": crypto["name"], "slug": crypto["slug"]}
    return None


async def get_crypto_price(token_id, token_slug):
    params = {"slug": token_slug, "convert": "USD"}
    response = await fetch(CMC_QUOTES_URL, params)
    if response.status_code == 200:
        data = response.json()
        return data["data"][str(token_id)]["quote"]["USD"]["price"]
    return None


async def send_telegram_message(message):
    params = {"chat_id": CHAT_ID, "text": message}
    response = await fetch(TG_URL, params)
    return response.json()


async def main():
    while True:
        token_name = input("Введите название криптовалюты (или 'N' для завершения ввода): ").strip()
        if token_name.lower() == "n":
            break
        crypto_info = await get_crypto_info(token_name)
        if not crypto_info:
            print("Криптовалюта не найдена. Попробуйте снова.")
            continue
        buy_price = float(input("Введите цену входа: "))
        tokens.append(
            {"id": crypto_info["id"], "slug": crypto_info["slug"], "name": crypto_info["name"], "buy_price": buy_price})

    while True:
        for token in tokens:
            mark_price = await get_crypto_price(token["id"], token["slug"])
            if mark_price is None:
                print(f"Ошибка получения цены для {token['name']}, пробуем снова...")
                continue
            percent = (mark_price - token["buy_price"]) / token["buy_price"] * 100
            current_datetime = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            message = (
                f"📊 {token['name']}\n"
                f"💰 Текущая цена: {mark_price:.2f}$\n"
                f"💲 Цена входа: {token['buy_price']:.2f}$\n"
                f"📈 Позиция от входа: {percent:.2f}%\n"
                f"⏳ Время: {current_datetime}\n"
            )
            print(message)
            if percent < loss:
                await send_telegram_message(message)
        await asyncio.sleep(60)


if __name__ == '__main__':
    asyncio.run(main())
