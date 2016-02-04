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
import asyncore, asynchat
import ssl
import smtpd

__all__ = ["SMTPServer", "DebuggingServer", "PureProxy", "MailmanProxy"]

__version__ = smtpd.__version__ + " (TLS and STARTTLS enabled)" 
program = sys.argv[0]

class SMTPChannel(smtpd.SMTPChannel):

    def smtp_EHLO(self, arg):
        if not arg:
            self.push('501 Syntax: HELO hostname')
            return
        if self.__greeting:
            self.push('503 Duplicate HELO/EHLO')
        else:
            self.__greeting = arg
            if isinstance(self.__conn,ssl.SSLSocket):
                self.push('250 %s' % self.__fqdn)
            else:
                self.push('250-%s' % self.__fqdn)
                self.push('250 STARTTLS')
    
    def smtp_STARTTLS(self, arg):
        if arg:
            self.push('501 Syntax error (no parameters allowed)')
        elif self.__server.starttls and not isinstance(self.__conn,ssl.SSLSocket):
            self.push('220 Ready to start TLS')
            self.__conn.settimeout(30)
            self.__conn = self.__server.ssl_ctx.wrap_socket(self.__conn, server_side=True)
            self.__conn.settimeout(None)
            # re-init channel
            asynchat.async_chat.__init__(self, self.__conn)
            self.__line = []
            self.__state = self.COMMAND
            self.__greeting = 0
            self.__mailfrom = None
            self.__rcpttos = []
            self.__data = ''
            print >> smtpd.DEBUGSTREAM, 'Peer: %s - negotiated TLS: %s' % (repr(self.__addr), repr(self.__conn.cipher()))
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
                print >> smtpd.DEBUGSTREAM, 'Peer: %s - negotiated TLS: %s' % (repr(addr), repr(conn.cipher()))
            channel = SMTPChannel(self, conn, addr)

class DebuggingServer(SMTPServer):
    # Do something with the gathered message
    def process_message(self, peer, mailfrom, rcpttos, data):
        inheaders = 1
        lines = data.split('\n')
        print '---------- MESSAGE FOLLOWS ----------'
        for line in lines:
            # headers first
            if inheaders and not line:
                print 'X-Peer:', peer[0]
                inheaders = 0
            print line
        print '------------ END MESSAGE ------------'

class PureProxy(SMTPServer):
    def process_message(self, peer, mailfrom, rcpttos, data):
        lines = data.split('\n')
        # Look for the last header
        i = 0
        for line in lines:
            if not line:
                break
            i += 1
        lines.insert(i, 'X-Peer: %s' % peer[0])
        data = NEWLINE.join(lines)
        refused = self._deliver(mailfrom, rcpttos, data)
        # TBD: what to do with refused addresses?
        print >> DEBUGSTREAM, 'we got some refusals:', refused

    def _deliver(self, mailfrom, rcpttos, data):
        import smtplib
        refused = {}
        try:
            s = smtplib.SMTP()
            s.connect(self._remoteaddr[0], self._remoteaddr[1])
            try:
                refused = s.sendmail(mailfrom, rcpttos, data)
            finally:
                s.quit()
        except smtplib.SMTPRecipientsRefused, e:
            print >> DEBUGSTREAM, 'got SMTPRecipientsRefused'
            refused = e.recipients
        except (socket.error, smtplib.SMTPException), e:
            print >> DEBUGSTREAM, 'got', e.__class__
            # All recipients were refused.  If the exception had an associated
            # error code, use it.  Otherwise,fake it with a non-triggering
            # exception code.
            errcode = getattr(e, 'smtp_code', -1)
            errmsg = getattr(e, 'smtp_error', 'ignore')
            for r in rcpttos:
                refused[r] = (errcode, errmsg)
        return refused


class MailmanProxy(PureProxy):
    def process_message(self, peer, mailfrom, rcpttos, data):
        from cStringIO import StringIO
        from Mailman import Utils
        from Mailman import Message
        from Mailman import MailList
        # If the message is to a Mailman mailing list, then we'll invoke the
        # Mailman script directly, without going through the real smtpd.
        # Otherwise we'll forward it to the local proxy for disposition.
        listnames = []
        for rcpt in rcpttos:
            local = rcpt.lower().split('@')[0]
            # We allow the following variations on the theme
            #   listname
            #   listname-admin
            #   listname-owner
            #   listname-request
            #   listname-join
            #   listname-leave
            parts = local.split('-')
            if len(parts) > 2:
                continue
            listname = parts[0]
            if len(parts) == 2:
                command = parts[1]
            else:
                command = ''
            if not Utils.list_exists(listname) or command not in (
                    '', 'admin', 'owner', 'request', 'join', 'leave'):
                continue
            listnames.append((rcpt, listname, command))
        # Remove all list recipients from rcpttos and forward what we're not
        # going to take care of ourselves.  Linear removal should be fine
        # since we don't expect a large number of recipients.
        for rcpt, listname, command in listnames:
            rcpttos.remove(rcpt)
        # If there's any non-list destined recipients left,
        print >> DEBUGSTREAM, 'forwarding recips:', ' '.join(rcpttos)
        if rcpttos:
            refused = self._deliver(mailfrom, rcpttos, data)
            # TBD: what to do with refused addresses?
            print >> DEBUGSTREAM, 'we got refusals:', refused
        # Now deliver directly to the list commands
        mlists = {}
        s = StringIO(data)
        msg = Message.Message(s)
        # These headers are required for the proper execution of Mailman.  All
        # MTAs in existence seem to add these if the original message doesn't
        # have them.
        if not msg.getheader('from'):
            msg['From'] = mailfrom
        if not msg.getheader('date'):
            msg['Date'] = time.ctime(time.time())
        for rcpt, listname, command in listnames:
            print >> DEBUGSTREAM, 'sending message to', rcpt
            mlist = mlists.get(listname)
            if not mlist:
                mlist = MailList.MailList(listname, lock=0)
                mlists[listname] = mlist
            # dispatch on the type of command
            if command == '':
                # post
                msg.Enqueue(mlist, tolist=1)
            elif command == 'admin':
                msg.Enqueue(mlist, toadmin=1)
            elif command == 'owner':
                msg.Enqueue(mlist, toowner=1)
            elif command == 'request':
                msg.Enqueue(mlist, torequest=1)
            elif command in ('join', 'leave'):
                # TBD: this is a hack!
                if command == 'join':
                    msg['Subject'] = 'subscribe'
                else:
                    msg['Subject'] = 'unsubscribe'
                msg.Enqueue(mlist, torequest=1)



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
            ['class=', 'nosetuid', 'version', 'help', 'debug', 'keyfile=', 'tls', 'starttls'])
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
            options.sslctx = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
            options.sslctx.load_cert_chain(certfile=arg, keyfile=arg)
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
