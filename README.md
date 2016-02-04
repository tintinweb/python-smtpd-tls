# smtpd-tls

An extension to the python 2.x smtpd standard library implementing implicit/explicit (STARTTLS) SSL/TLS support

* added STARTTLS handling
* added implicit tls

just pass a configured ssl.context (certs, keys, protocols, auth, ...) to smtpd-tls.SMTPServer()

original smtpd pydoc: https://docs.python.org/2/library/smtpd.html

**Requires Python 2.7 or higher**

# Install

from pip

    pip install smtpd-tls

from source

    python setup.py install

verify:

    #> python -c "import smtpd_tls; echo smtpd_tls"
    #> python -m smptd_tls --help

# Example

STARTTLS via smtp port 25:

    #> python -m smtpd_tls --debug -c DebuggingServer --starttls --keyfile=../server.pem 0.0.0.0:25
    DebuggingServer started at Thu Feb  4 16:57:06 2016
            Local addr: ('0.0.0.0', 25)
            Remote addr:('mail.somehost.com', 25)
            TLS Mode: explicit (plaintext until STARTTLS)
            TLS Context: <ssl.SSLContext object at 0x7f8fd8adbbb0>
    Incoming connection from ('192.168.139.1', 39983)
    Peer: ('192.168.139.1', 39983)
    Data: 'ehlo [192.168.139.1]'
    Data: 'STARTTLS'
    Peer: ('192.168.139.1', 39983) - negotiated TLS: ('ECDHE-RSA-AES256-GCM-SHA384', 'TLSv1/SSLv3', 256)
    Data: 'ehlo [192.168.139.1]'
    Data: 'mail FROM:<sender@example.com>'
    ===> MAIL FROM:<sender@example.com>
    sender: sender@example.com
    Data: 'rcpt TO:<user@example.com>'
    ===> RCPT TO:<user@example.com>
    recips: ['user@example.com']
    Data: 'data'
    Data: "From: sender@example.com\r\nTo: user@example.com\r\nSubject: Hello!\r\n\r\nThis message was sent with Python's smtplib."
    ---------- MESSAGE FOLLOWS ----------
    From: sender@example.com
    To: user@example.com
    Subject: Hello!
    X-Peer: 192.168.139.1

    This message was sent with Python's smtplib.
    ------------ END MESSAGE ------------
    Data: 'quit'


Implicit TLS via smtp port 465:

    #> python -m smtpd_tls --debug -c DebuggingServer --tls --keyfile=../server.pem 0.0.0.0:465
    DebuggingServer started at Thu Feb  4 17:00:53 2016
            Local addr: ('0.0.0.0', 465)
            Remote addr:('mail.somehost.com', 25)
            TLS Mode: implicit (encrypted from the beginning)
            TLS Context: <ssl.SSLContext object at 0x7fee6ec36bb0>
    Incoming connection from ('192.168.139.1', 40028)
    Peer: ('192.168.139.1', 40028) - negotiated TLS: ('ECDHE-RSA-AES256-GCM-SHA384', 'TLSv1/SSLv3', 256)
    Peer: ('192.168.139.1', 40028)
    Data: 'ehlo [192.168.139.1]'
    Data: 'mail FROM:<sender@example.com>'
    ===> MAIL FROM:<sender@example.com>
    sender: sender@example.com
    Data: 'rcpt TO:<user@example.com>'
    ===> RCPT TO:<user@example.com>
    recips: ['user@example.com']
    Data: 'data'
    Data: "From: sender@example.com\r\nTo: user@example.com\r\nSubject: Hello!\r\n\r\nThis message was sent with Python's smtplib."
    ---------- MESSAGE FOLLOWS ----------
    From: sender@example.com
    To: user@example.com
    Subject: Hello!
    X-Peer: 192.168.139.1

    This message was sent with Python's smtplib.
    ------------ END MESSAGE ------------
    Data: 'quit'
