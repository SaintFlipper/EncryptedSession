
import random
from flask import Flask, render_template, session, request
from encrypted_session import EncryptedSessionInterface

app = Flask(__name__)

# Encryption key for AES256 (must be 32 bytes long)
# Can generate this with:
# from Crypto.Random import get_random_bytes
# key = get_random_bytes(32)
# print (key)

app.crypto_key = b'\xcb\xf2\x19H\xd9l\x05\xc7j\xb2\xd0^}B*\x8d\xb6\x8aPd\x1c%\x83\x1e_\xf0\xb9C\xa9XOC'

# Replace default session implementation
app.session_interface = EncryptedSessionInterface()

@app.route ('/', methods=['GET'])
def root():
    r = random.randint (1,10)
    session['randint'] = r
    
    return render_template ('test_form.html')

@app.route ('/', methods=['POST'])
def form_handler():
    guess = int(request.form['guess'])
    if guess == session['randint']:
        status = "RIGHT"
    else:
        status = "WRONG"
        
    m = {'guess': guess, 'status': status}
    return render_template ('test_form.html', m=m)


if __name__ == '__main__':
    app.run(threaded=True)
