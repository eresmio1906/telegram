from cryptography.fernet import Fernet

KEY = b"fPhWsIryZNqWV5x_82_D-EX4KjMzCOIto-VCxcUblRI="
f = Fernet(KEY)

bot_token = input("BOT_TOKEN: ").encode()
api_key = input("API_KEY: ").encode()
user_id = input("USER_ID: ").encode()

print("ENC_BOT_TOKEN=", f.encrypt(bot_token).decode())
print("ENC_API_KEY=", f.encrypt(api_key).decode())
print("ENC_USER_ID=", f.encrypt(user_id).decode())