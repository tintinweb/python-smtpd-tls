#! /usr/bin/env python
# -*- coding: UTF-8 -*-
# Author : tintinweb@oststrom.com <github.com/tintinweb>
"""An RFC 2821 smtp proxy with implicit TLS and explicit STARTTLS (RFC 3207) support

Usage: %(program)s [options] [localhost:localport [remotehost:remoteport]]

Options:

    --nosetuid
    -n
        This program generally tries to setuid `nobody', unless this flag is
        set.  The setuid call will fail if this program is not run as root (in
        which case, use this flag).

    --version
    -V
        Print the version number and exit.

    --class classname
    -c classname
        Use `classname' as the concrete SMTP proxy class.  Uses `PureProxy' by
        default.

    --debug
    -d
        Turn on debugging prints.

    --keyfile
    -k
        ssl private key and certificate file (server.pem)
        
    --tls
    -t
        implicit TLS mode (cannot be combined with --starttls)
    
    --starttls
    -s
        explicit RFC 3207 STARTTLS mode (cannot be combined with --tls) 

    --help
    -h
        Print this message and exit.

Version: %(__version__)s

If localhost is not given then `localhost' is used, and if localport is not
given then 8025 is used.  If remotehost is not given then `localhost' is used,
and if remoteport is not given, then 25 is used.
"""
import sys
import os
import getopt
import asyncore
import ssl
import smtpd

__all__ = ["SMTPServer","DebuggingServer","PureProxy","MailmanProxy"]

__version__ = smtpd.__version__ + " (TLS and STARTTLS enabled)" 
program = sys.argv[0]

class SMTPChannel(smtpd.SMTPChannel):
    def smtp_STARTTLS(self, arg):
        if arg:
            self.push('501 Syntax error (no parameters allowed)')
        elif self.__server.starttls and not isinstance(self.__conn,ssl.SSLSocket):
            self.push('220 Ready to start TLS')
            self.__conn.settimeout(30)
            self.__conn = self.__server.ssl_ctx.wrap_socket(self.__conn, server_side=True)
            # re-init the channel
            self = SMTPChannel(self.__server, self.__conn, self.__addr)
            self.__conn.settimeout(None)
        else:
            self.push('454 TLS not available due to temporary reason')

class SMTPServer(smtpd.SMTPServer):
    def __init__(self, localaddr, remoteaddr, ssl_ctx=None, starttls=True):
        self.ssl_ctx = ssl_ctx
        self.starttls = starttls
        smtpd.SMTPServer.__init__(self, localaddr, remoteaddr)
        print >> smtpd.DEBUGSTREAM, '\tTLS Mode: %s\n\tTLS Context: %s' % ('explicit (plaintext until STARTTLS)' if starttls else 'implicit (encrypted from the beginning)', 
                                                                           repr(ssl_ctx))
        
    def handle_accept(self):
        pair = self.accept()
        if pair is not None:
            conn, addr = pair
            print >> smtpd.DEBUGSTREAM, 'Incoming connection from %s' % repr(addr)
            if self.ssl_ctx and not self.starttls:
                conn = self.ssl_ctx.wrap_socket(conn, server_side=True)
            channel = SMTPChannel(self, conn, addr)

# ReLink implementations
class DebuggingServer(SMTPServer, smtpd.DebuggingServer): pass
class PureProxy(SMTPServer, smtpd.PureProxy): pass
class MailmanProxy(SMTPServer, smtpd.MailmanProxy): pass

class Options:
    setuid = 1
    classname = 'PureProxy'
    sslctx = None
    starttls = True


def usage(code, msg=''):
    print >> sys.stderr, __doc__ % globals()
    if msg:
        print >> sys.stderr, msg
    sys.exit(code)
    
def parseargs():
    global DEBUGSTREAM
    try:
        opts, args = getopt.getopt(
            sys.argv[1:], 'nVhc:dk:ts',
            ['class=', 'nosetuid', 'version', 'help', 'debug', 'keyfile', 'tls', 'starttls'])
    except getopt.error, e:
        usage(1, e)

    options = Options()
    for opt, arg in opts:
        if opt in ('-h', '--help'):
            usage(0)
        elif opt in ('-V', '--version'):
            print >> sys.stderr, __version__
            sys.exit(0)
        elif opt in ('-n', '--nosetuid'):
            options.setuid = 0
        elif opt in ('-c', '--class'):
            options.classname = arg
        elif opt in ('-d', '--debug'):
            smtpd.DEBUGSTREAM = sys.stderr
        elif opt in ('-k', '--keyfile'):
            options.sslctx  = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
            options.sslctx .load_cert_chain(certfile=arg, keyfile=arg)
        elif opt in ('-t', '--tls'):
            options.starttls = False
        elif opt in ('-s', '--starttls'):
            options.starttls = True

    # parse the rest of the arguments
    if len(args) < 1:
        localspec = 'localhost:8025'
        remotespec = 'localhost:25'
    elif len(args) < 2:
        localspec = args[0]
        remotespec = 'localhost:25'
    elif len(args) < 3:
        localspec = args[0]
        remotespec = args[1]
    else:
        usage(1, 'Invalid arguments: %s' % COMMASPACE.join(args))

    # split into host/port pairs
    i = localspec.find(':')
    if i < 0:
        usage(1, 'Bad local spec: %s' % localspec)
    options.localhost = localspec[:i]
    try:
        options.localport = int(localspec[i+1:])
    except ValueError:
        usage(1, 'Bad local port: %s' % localspec)
    i = remotespec.find(':')
    if i < 0:
        usage(1, 'Bad remote spec: %s' % remotespec)
    options.remotehost = remotespec[:i]
    try:
        options.remoteport = int(remotespec[i+1:])
    except ValueError:
        usage(1, 'Bad remote port: %s' % remotespec)
    return options

if __name__ == '__main__':
    options = parseargs()
    # Become nobody
    classname = options.classname
    if "." in classname:
        lastdot = classname.rfind(".")
        mod = __import__(classname[:lastdot], globals(), locals(), [""])
        classname = classname[lastdot+1:]
    else:
        import __main__ as mod
    class_ = getattr(mod, classname)
    proxy = class_((options.localhost, options.localport),
                   (options.remotehost, options.remoteport), options.sslctx, options.starttls)
    if options.setuid:
        try:
            import pwd
        except ImportError:
            print >> sys.stderr, \
                  'Cannot import module "pwd"; try running with -n option.'
            sys.exit(1)
        nobody = pwd.getpwnam('nobody')[2]
        try:
            os.setuid(nobody)
        except OSError, e:
            if e.errno != errno.EPERM: raise
            print >> sys.stderr, \
                  'Cannot setuid "nobody"; try running with -n option.'
            sys.exit(1)
    try:
        asyncore.loop()
    except KeyboardInterrupt:
        pass
