# smtpd-tls

An extension to the python 2.x smtpd standard library implementing implicit/explicit (STARTTLS) SSL/TLS support

* added STARTTLS handling
* added implicit tls

just pass a configured ssl.context (certs, keys, protocols, auth, ...) to smtpd-tls.SMTPServer()

original smtpd pydoc: https://docs.python.org/2/library/smtpd.html

# Install

from pip

    pip install smtpd-tls

from source

    python setup.py install

verify:

    #> python -c "import smtpd_tls"
    #> python -m smptd_tls --help

# Example

starttls smtp daemon:

    #> python -m smtpd_tls --debug -c DebuggingServer --keyfile server.pem --starttls
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


    #> python -m smtpd_tls --debug -c DebuggingServer --keyfile server.pem --tls
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
