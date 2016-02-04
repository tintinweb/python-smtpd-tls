# python-smtpd
An extension to the python 2.x smtpd standard library implementing implicit/explicit (STARTTLS) SSL/TLS support

# Example

    python ../ssmtpd.py  --debug -c DebuggingServer -k ../server.pem --starttls --tls --starttls --tls --starttls
    DebuggingServer started at Thu Feb  4 12:30:04 2016
            Local addr: ('localhost', 8025)
            Remote addr:('localhost', 25)
            TLS Mode: explicit (plaintext until STARTTLS)
            TLS Context: <ssl.SSLContext object at 0x7ff9ee6ee8d8>
    Incoming connection from ('127.0.0.1', 33485)
    Peer: ('127.0.0.1', 33485)
    Data: 'EHLO openssl.client.net'
    Data: 'STARTTLS'
    Peer: ('127.0.0.1', 33485)
    Data: 'HELO aa'
    Data: 'quit'
