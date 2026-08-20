import discord
import base64
import hashlib
from discord import app_commands

class CipherProcessor:
    def __init__(self):
        self.morse_dict = {
            'A': '.-', 'B': '-...', 'C': '-.-.', 'D': '-..', 'E': '.', 'F': '..-.', 'G': '--.',
            'H': '....', 'I': '..', 'J': '.---', 'K': '-.-', 'L': '.-..', 'M': '--', 'N': '-.',
            'O': '---', 'P': '.--.', 'Q': '--.-', 'R': '.-.', 'S': '...', 'T': '-', 'U': '..-',
            'V': '...-', 'W': '.--', 'X': '-..-', 'Y': '-.--', 'Z': '--..',
            '0': '-----', '1': '.----', '2': '..---', '3': '...--', '4': '....-', '5': '.....',
            '6': '-....', '7': '--...', '8': '---..', '9': '----.',
            'А': '.-', 'Б': '-...', 'В': '.--', 'Г': '--.', 'Д': '-..', 'Е': '.', 'Ё': '.',
            'Ж': '...-', 'З': '--..', 'И': '..', 'Й': '.---', 'К': '-.-', 'Л': '.-..', 'М': '--',
            'Н': '-.', 'О': '---', 'П': '.--.', 'Р': '.-.', 'С': '...', 'Т': '-', 'У': '..-',
            'Ф': '..-.', 'Х': '....', 'Ц': '-.-.', 'Ч': '---.', 'Ш': '----', 'Щ': '--.-',
            'Ъ': '.--.-.', 'Ы': '-.--', 'Ь': '-..-', 'Э': '..-..', 'Ю': '..--', 'Я': '.-.-',
            ' ': '/'
        }
        self.reverse_morse = {v: k for k, v in self.morse_dict.items()}
        self.russian_upper = "АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ"
        self.russian_lower = "абвгдеёжзийклмнопрстуфхцчшщъыьэюя"
        self.english_upper = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        self.english_lower = "abcdefghijklmnopqrstuvwxyz"

    def _is_russian(self, char: str) -> bool:
        return 'А' <= char <= 'я' or char in 'Ёё'

    def caesar(self, text: str, shift: int, encrypt: bool = True) -> str:
        result = []
        shift_amount = shift if encrypt else -shift
        for char in text:
            if char.isalpha():
                if self._is_russian(char):
                    if char.isupper():
                        alphabet = self.russian_upper
                    else:
                        alphabet = self.russian_lower
                    idx = (alphabet.index(char) + shift_amount) % len(alphabet)
                    result.append(alphabet[idx])
                else:
                    if char.isupper():
                        result.append(chr((ord(char) - 65 + shift_amount) % 26 + 65))
                    else:
                        result.append(chr((ord(char) - 97 + shift_amount) % 26 + 97))
            else:
                result.append(char)
        return ''.join(result)

    def atbash(self, text: str) -> str:
        result = []
        for char in text:
            if char.isalpha():
                if self._is_russian(char):
                    if char.isupper():
                        alphabet = self.russian_upper
                        idx = alphabet.index(char)
                        result.append(alphabet[len(alphabet) - 1 - idx])
                    else:
                        alphabet = self.russian_lower
                        idx = alphabet.index(char)
                        result.append(alphabet[len(alphabet) - 1 - idx])
                else:
                    if char.isupper():
                        result.append(chr(155 - ord(char)))
                    else:
                        result.append(chr(219 - ord(char)))
            else:
                result.append(char)
        return ''.join(result)

    def rot13(self, text: str) -> str:
        result = []
        for char in text:
            if char.isalpha():
                if self._is_russian(char):
                    if char.isupper():
                        alphabet = self.russian_upper
                    else:
                        alphabet = self.russian_lower
                    idx = (alphabet.index(char) + 16) % len(alphabet)
                    result.append(alphabet[idx])
                else:
                    if char.isupper():
                        result.append(chr((ord(char) - 65 + 13) % 26 + 65))
                    else:
                        result.append(chr((ord(char) - 97 + 13) % 26 + 97))
            else:
                result.append(char)
        return ''.join(result)

    def vigenere(self, text: str, key: str, encrypt: bool = True) -> str:
        result = []
        key_index = 0
        for char in text:
            if char.isalpha():
                key_char = key[key_index % len(key)]
                if self._is_russian(char):
                    if char.isupper():
                        alphabet = self.russian_upper
                    else:
                        alphabet = self.russian_lower
                    if self._is_russian(key_char):
                        key_alphabet = self.russian_upper if key_char.isupper() else self.russian_lower
                    else:
                        key_alphabet = self.english_upper if key_char.isupper() else self.english_lower
                    char_idx = alphabet.index(char)
                    key_idx = key_alphabet.index(key_char) if key_char in key_alphabet else 0
                    new_idx = (char_idx + key_idx) % len(alphabet) if encrypt else (char_idx - key_idx) % len(alphabet)
                    result.append(alphabet[new_idx])
                else:
                    shift = ord(key_char.upper()) - 65
                    if not encrypt:
                        shift = -shift
                    if char.isupper():
                        result.append(chr((ord(char) - 65 + shift) % 26 + 65))
                    else:
                        result.append(chr((ord(char) - 97 + shift) % 26 + 97))
                key_index += 1
            else:
                result.append(char)
        return ''.join(result)

    def base64_encode(self, text: str) -> str:
        return base64.b64encode(text.encode('utf-8')).decode('utf-8')

    def base64_decode(self, text: str) -> str:
        try:
            return base64.b64decode(text.encode('utf-8')).decode('utf-8')
        except:
            return "❌ Ошибка декодирования Base64"

    def morse_encode(self, text: str) -> str:
        text = text.upper()
        result = []
        for char in text:
            result.append(self.morse_dict.get(char, '?'))
        return ' '.join(result)

    def morse_decode(self, text: str) -> str:
        words = text.split(' / ')
        result = []
        for word in words:
            chars = word.split()
            decoded_word = ''.join(self.reverse_morse.get(char, '?') for char in chars)
            result.append(decoded_word)
        return ' '.join(result)

    def hex_encode(self, text: str) -> str:
        return text.encode('utf-8').hex()

    def hex_decode(self, text: str) -> str:
        try:
            return bytes.fromhex(text).decode('utf-8')
        except:
            return "❌ Ошибка декодирования HEX"

    def binary_encode(self, text: str) -> str:
        return ' '.join(format(ord(c), '08b') for c in text)

    def binary_decode(self, text: str) -> str:
        try:
            binary_values = text.split()
            return ''.join(chr(int(b, 2)) for b in binary_values)
        except:
            return "❌ Ошибка декодирования бинарного кода"

    def xor_cipher(self, text: str, key: str) -> str:
        result = []
        for i, char in enumerate(text):
            result.append(chr(ord(char) ^ ord(key[i % len(key)])))
        return base64.b64encode(''.join(result).encode('utf-8')).decode('utf-8')

    def xor_decipher(self, text: str, key: str) -> str:
        try:
            decoded = base64.b64decode(text.encode('utf-8')).decode('utf-8')
            result = []
            for i, char in enumerate(decoded):
                result.append(chr(ord(char) ^ ord(key[i % len(key)])))
            return ''.join(result)
        except:
            return "❌ Ошибка декодирования XOR"

    def affine_encrypt(self, text: str, a: int = 5, b: int = 8) -> str:
        result = []
        for char in text:
            if char.isalpha():
                if self._is_russian(char):
                    alphabet_size = 33
                    if char.isupper():
                        base = ord('А')
                    else:
                        base = ord('а')
                    x = ord(char) - base
                    result.append(chr(((a * x + b) % alphabet_size) + base))
                else:
                    alphabet_size = 26
                    if char.isupper():
                        base = ord('A')
                    else:
                        base = ord('a')
                    x = ord(char) - base
                    result.append(chr(((a * x + b) % alphabet_size) + base))
            else:
                result.append(char)
        return ''.join(result)

    def affine_decrypt(self, text: str, a: int = 5, b: int = 8) -> str:
        result = []
        for char in text:
            if char.isalpha():
                if self._is_russian(char):
                    alphabet_size = 33
                    if char.isupper():
                        base = ord('А')
                    else:
                        base = ord('а')
                    a_inv = 0
                    for i in range(alphabet_size):
                        if (a * i) % alphabet_size == 1:
                            a_inv = i
                            break
                    y = ord(char) - base
                    result.append(chr(((a_inv * (y - b)) % alphabet_size) + base))
                else:
                    alphabet_size = 26
                    if char.isupper():
                        base = ord('A')
                    else:
                        base = ord('a')
                    a_inv = 0
                    for i in range(alphabet_size):
                        if (a * i) % alphabet_size == 1:
                            a_inv = i
                            break
                    y = ord(char) - base
                    result.append(chr(((a_inv * (y - b)) % alphabet_size) + base))
            else:
                result.append(char)
        return ''.join(result)

    def md5_hash(self, text: str) -> str:
        return hashlib.md5(text.encode('utf-8')).hexdigest()

    def sha1_hash(self, text: str) -> str:
        return hashlib.sha1(text.encode('utf-8')).hexdigest()

    def sha256_hash(self, text: str) -> str:
        return hashlib.sha256(text.encode('utf-8')).hexdigest()

    def sha512_hash(self, text: str) -> str:
        return hashlib.sha512(text.encode('utf-8')).hexdigest()

@bot.tree.command(name="cipher", description="Шифрование и расшифровка текста")
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@app_commands.user_install()
@app_commands.describe(
    action="Действие: шифровать или расшифровать",
    cipher_type="Тип шифра",
    text="Текст для обработки",
    key="Ключ (если требуется)",
    shift="Сдвиг для шифра Цезаря"
)
@app_commands.choices(
    action=[
        app_commands.Choice(name="🔒 Зашифровать", value="encrypt"),
        app_commands.Choice(name="🔓 Расшифровать", value="decrypt")
    ],
    cipher_type=[
        app_commands.Choice(name="🔁 Цезарь", value="caesar"),
        app_commands.Choice(name="🔁 Атбаш", value="atbash"),
        app_commands.Choice(name="🔁 ROT13", value="rot13"),
        app_commands.Choice(name="🔁 Виженер", value="vigenere"),
        app_commands.Choice(name="🔁 Base64", value="base64"),
        app_commands.Choice(name="🔁 Морзе", value="morse"),
        app_commands.Choice(name="🔁 HEX", value="hex"),
        app_commands.Choice(name="🔁 Бинарный", value="binary"),
        app_commands.Choice(name="🔁 XOR", value="xor"),
        app_commands.Choice(name="🔁 Аффинный", value="affine"),
        app_commands.Choice(name="🚫 MD5", value="md5"),
        app_commands.Choice(name="🚫 SHA-1", value="sha1"),
        app_commands.Choice(name="🚫 SHA-256", value="sha256"),
        app_commands.Choice(name="🚫 SHA-512", value="sha512"),
    ]
)
async def cipher(
    interaction: discord.Interaction,
    action: str,
    cipher_type: str,
    text: str,
    key: str = None,
    shift: int = 3
):
    await interaction.response.defer()
    processor = CipherProcessor()
    try:
        result = ""
        cipher_name = ""
        if cipher_type == "caesar":
            cipher_name = "Цезарь"
            if action == "encrypt":
                result = processor.caesar(text, shift, True)
            else:
                result = processor.caesar(text, shift, False)
        elif cipher_type == "atbash":
            cipher_name = "Атбаш"
            result = processor.atbash(text)
        elif cipher_type == "rot13":
            cipher_name = "ROT13"
            result = processor.rot13(text)
        elif cipher_type == "vigenere":
            cipher_name = "Виженер"
            if not key:
                await interaction.followup.send("❌ Для шифра Виженера требуется ключ!", ephemeral=True)
                return
            if action == "encrypt":
                result = processor.vigenere(text, key, True)
            else:
                result = processor.vigenere(text, key, False)
        elif cipher_type == "base64":
            cipher_name = "Base64"
            if action == "encrypt":
                result = processor.base64_encode(text)
            else:
                result = processor.base64_decode(text)
        elif cipher_type == "morse":
            cipher_name = "Морзе"
            if action == "encrypt":
                result = processor.morse_encode(text)
            else:
                result = processor.morse_decode(text)
        elif cipher_type == "hex":
            cipher_name = "HEX"
            if action == "encrypt":
                result = processor.hex_encode(text)
            else:
                result = processor.hex_decode(text)
        elif cipher_type == "binary":
            cipher_name = "Бинарный"
            if action == "encrypt":
                result = processor.binary_encode(text)
            else:
                result = processor.binary_decode(text)
        elif cipher_type == "xor":
            cipher_name = "XOR"
            if not key:
                await interaction.followup.send("❌ Для XOR шифра требуется ключ!", ephemeral=True)
                return
            if action == "encrypt":
                result = processor.xor_cipher(text, key)
            else:
                result = processor.xor_decipher(text, key)
        elif cipher_type == "affine":
            cipher_name = "Аффинный"
            if action == "encrypt":
                result = processor.affine_encrypt(text)
            else:
                result = processor.affine_decrypt(text)
        elif cipher_type == "md5":
            cipher_name = "MD5"
            result = processor.md5_hash(text)
        elif cipher_type == "sha1":
            cipher_name = "SHA-1"
            result = processor.sha1_hash(text)
        elif cipher_type == "sha256":
            cipher_name = "SHA-256"
            result = processor.sha256_hash(text)
        elif cipher_type == "sha512":
            cipher_name = "SHA-512"
            result = processor.sha512_hash(text)
        action_emoji = "🔒" if action == "encrypt" else "🔓"
        action_text = "Зашифровано" if action == "encrypt" else "Расшифровано"
        embed = discord.Embed(title=f"{action_emoji} {cipher_name} - {action_text}", color=discord.Color.blue())
        embed.add_field(name="📥 Исходный текст", value=f"```{text}```", inline=False)
        display_result = result[:1000] + "..." if len(result) > 1000 else result
        embed.add_field(name="📤 Результат", value=f"```{display_result}```", inline=False)
        if key:
            embed.add_field(name="🔑 Ключ", value=f"`{key}`", inline=True)
        if cipher_type == "caesar":
            embed.add_field(name="📏 Сдвиг", value=f"`{shift}`", inline=True)
        if cipher_type in ["md5", "sha1", "sha256", "sha512"]:
            embed.add_field(name="⚠️ Внимание", value="Это хэш-функция - результат не может быть расшифрован!", inline=False)
        await interaction.followup.send(embed=embed)
    except Exception as e:
        await interaction.followup.send(f"❌ Произошла ошибка при обработке: {str(e)}", ephemeral=True)