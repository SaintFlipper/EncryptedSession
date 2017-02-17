
from werkzeug.datastructures import CallbackDict
from flask.sessions import SessionInterface, SessionMixin

from Crypto.Cipher import AES
import json
import base64
import zlib

class EncryptedSession(CallbackDict, SessionMixin):

    def __init__(self, initial=None):
        def on_update(self):
            self.modified = True
        CallbackDict.__init__(self, initial, on_update)
        self.modified = False


class EncryptedSessionInterface(SessionInterface):
    session_class = EncryptedSession
    compress_threshold = 1024

    def open_session(self, app, request):
        '''
        @param py: Flask py
        @param request: Flask HTTP Request
        @summary: Sets the current session from the request's session cooke. This overrides the default
        Flask implementation, adding AES decryption of the client-side session cookie.
        '''

        # Get the session cookie
        session_cookie = request.cookies.get(app.session_cookie_name)
        if not session_cookie:
            return self.session_class()

        # Split the session cookie : <z|u>.<base64 cipher text>.<base64 mac>.<base64 nonce>
        itup = session_cookie.split(".")
        if (len (itup) is not 4):
            return self.session_class()     # Session cookie not in the right format

        try:

            # Compressed data?
            if (itup[0] == 'z'):            # session cookie for compressed data starts with "z."
                is_compressed = True
            else:
                is_compressed = False

            # Decode the cookie parts from base64
            ciphertext = base64.b64decode (bytes(itup[1], 'utf-8'))
            mac = base64.b64decode (bytes(itup[2], 'utf-8'))
            nonce = base64.b64decode (bytes(itup[3], 'utf-8'))

            # Decrypt
            cipher = AES.new (app.crypto_key, AES.MODE_EAX, nonce)
            data = cipher.decrypt_and_verify (ciphertext, mac)

            # Convert back to a dict and pass that onto the session
            if is_compressed:
                data = zlib.decompress (data)
            session_dict = json.loads (str (data, 'utf-8'))

            return self.session_class (session_dict)

        except ValueError:
            return self.session_class()

    def save_session(self, app, session, response):
        '''
        @param py: Flask py
        @param session: Flask / Werkzeug Session
        @param response: Flask HTTP Response
        @summary: Saves the current session. This overrides the default Flask implementation, adding
        AES encryption of the client-side session cookie.
        '''

        domain = self.get_cookie_domain(app)
        if not session:
            if session.modified:
                response.delete_cookie (app.session_cookie_name, domain=domain)
            return
        expires = self.get_expiration_time(app, session)

        # Decide whether to compress
        bdict = bytes (json.dumps (dict (session)), 'utf-8')
        if (len (bdict) > self.compress_threshold):
            prefix = "z"                                    # session cookie for compressed data starts with "z."
            bdict = zlib.compress (bdict)
        else:
            prefix = "u"                                    # session cookie for uncompressed data starts with "u."

        # Encrypt using AES in EAX mode
        cipher = AES.new (app.crypto_key, AES.MODE_EAX)
        ciphertext, mac = cipher.encrypt_and_digest (bdict)
        nonce = cipher.nonce

        # Convert the ciphertext, mac, and nonce to base64
        b64_ciphertext = base64.b64encode (ciphertext)
        b64_mac = base64.b64encode (mac)
        b64_nonce = base64.b64encode (nonce)

        # Create the session cookie as <u|z>.<base64 cipher text>.<base64 mac>.<base64 nonce>
        tup = [prefix, b64_ciphertext.decode(), b64_mac.decode(), b64_nonce.decode()]
        session_cookie = ".".join(tup)

        # Set the session cookie
        response.set_cookie(app.session_cookie_name, session_cookie,
                            expires=expires, httponly=True,
                            domain=domain)

