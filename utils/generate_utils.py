import pyotp

class GenerateOTP:
    @classmethod
    def generate_otp(cls):
        secret_key = pyotp.random_base32()
        totp = pyotp.TOTP(secret_key, interval=1)
        otp = totp.now()
        return otp

