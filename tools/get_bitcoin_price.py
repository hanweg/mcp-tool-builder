
def get_bitcoin_price():
    from urllib import request, error
    import json
    try:
        with request.urlopen('https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd') as response:
            data = json.loads(response.read())
            return f"Current Bitcoin price: ${data['bitcoin']['usd']:,.2f}"
    except:
        return "Error: Unable to fetch Bitcoin price"
